from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Callable
import os
import statistics as stats
import pandas as pd

from wasi_analyst.core.market import Market
from wasi_analyst.core.orderbook import Trade
from wasi_analyst.agents.base import AgentState
from wasi_analyst.agents.fundamental_agent import FundamentalAgent
from wasi_analyst.agents.macro_agent import MacroAgent
from wasi_analyst.agents.sentiment_agent import SentimentAgent
from wasi_analyst.agents.risk_manager import RiskManager
from wasi_analyst.agents.execution_agent import ExecutionAgent
from wasi_analyst.util.config import WasiConfig
from wasi_analyst.util.store import DuckDBStore


@dataclass
class Coordinator:
    cfg: WasiConfig
    market: Market
    store: DuckDBStore

    def _features_from_history(self, prices: List[float]) -> Dict:
        """Calcula features con ventanas definidas en config."""
        w_sma = max(1, self.cfg.fundamental_sma_window)
        w_mom = max(1, self.cfg.macro_mom_window)
        w_vol = max(2, self.cfg.sentiment_break_window)  # usamos misma long como proxy
        w_brk = max(2, self.cfg.sentiment_break_window)

        p = prices[-1]
        sma = sum(prices[-w_sma:]) / min(len(prices), w_sma)
        mom = p / prices[-w_mom] - 1.0 if len(prices) > w_mom else 0.0

        rets = []
        if len(prices) > 1:
            win = min(len(prices) - 1, w_vol)
            for a, b in zip(prices[-win-1:-1], prices[-win:]):
                if a > 0:
                    rets.append(b / a - 1.0)
        vol = float(stats.pstdev(rets)) if len(rets) >= 2 else 0.0

        hi = max(prices[-w_brk:]) if prices else p
        lo = min(prices[-w_brk:]) if prices else p

        return {"price": p, "sma": sma, "mom": mom, "vol": vol, "hi": hi, "lo": lo}

    def run(
        self,
        return_dataframes: bool = False,
        user_goal: str = "",
        loop_report: Callable[[int, str], None] | None = None,
    ) -> Optional[Tuple[pd.DataFrame, pd.DataFrame, List[str], List[dict]]]:

        os.makedirs("artifacts", exist_ok=True)

        state = AgentState(cash=self.cfg.cash0, positions={s: 0 for s in self.cfg.symbols})
        self._state = state
        price_hist: Dict[str, List[float]] = {s: [] for s in self.cfg.symbols}

        f = FundamentalAgent("fundamental", self.cfg, state, mode=self.cfg.fundamental_mode)
        m = MacroAgent("macro", self.cfg, state, mode=self.cfg.macro_mode)
        s = SentimentAgent("sentiment", self.cfg, state, mode=self.cfg.sentiment_mode)
        r = RiskManager("risk", self.cfg, state)
        x = ExecutionAgent("exec", self.cfg, state)

        history_rows: List[Dict] = []
        trades_rows: List[Dict] = []
        notes: List[str] = [f"User goal: {user_goal}" if user_goal else "No user goal provided."]
        transcript: List[dict] = []

        for d in range(self.cfg.days):
            if loop_report: loop_report(d, "tick-precios")
            self.market.step_prices()
            snapshot = self.market.snapshot_prices()
            for sym, px in snapshot.items():
                price_hist[sym].append(float(px))

            obs = {"symbols": {sym: self._features_from_history(price_hist[sym])
                               for sym in self.cfg.symbols}}

            if loop_report: loop_report(d, "agents")
            f_dec = f.decide(obs, user_goal=user_goal)
            m_dec = m.decide(obs, user_goal=user_goal)
            s_dec = s.decide(obs, user_goal=user_goal)
            transcript.append({
                "day": d, "step": "agents_opinion",
                "messages": [
                    {"agent": "fundamental", **f_dec},
                    {"agent": "macro", **m_dec},
                    {"agent": "sentiment", **s_dec},
                ],
            })

            if loop_report: loop_report(d, "merge")
            merged = self._merge_actions(
                f_dec.get("actions", []) + m_dec.get("actions", []) + s_dec.get("actions", []), obs
            )
            transcript.append({"day": d, "step": "merge", "actions": merged})

            if loop_report: loop_report(d, "risk")
            gated = r.enforce(merged, obs)
            transcript.append({"day": d, "step": "risk_manager", "actions": gated})

            if loop_report: loop_report(d, "exec")
            orders = x.to_orders(gated)
            transcript.append({"day": d, "step": "execution_agent",
                               "orders": [o.__dict__ for o in orders]})

            for o in orders:
                if o.qty > 0:
                    self.market.place(o)
            trades = self.market.match_all()
            self._apply_trades(trades)
            for t in trades:
                trades_rows.append({
                    "day": d, "symbol": t.symbol, "price": t.price, "qty": t.qty,
                    "buy_agent": t.buy_agent, "sell_agent": t.sell_agent
                })

            equity = state.cash + sum(q * snapshot[sym] for sym, q in state.positions.items())
            history_rows.append({
                "day": d,
                **{f"px_{k}": v for k, v in snapshot.items()},
                "cash": state.cash,
                **{f"pos_{k}": v for k, v in state.positions.items()},
                "equity": equity
            })

        if loop_report: loop_report(self.cfg.days - 1, "persist")

        hist_df = pd.DataFrame(history_rows)
        trades_df = pd.DataFrame(trades_rows) if trades_rows else pd.DataFrame(
            columns=["day","symbol","price","qty","buy_agent","sell_agent"]
        )
        hist_df.to_parquet("artifacts/history.parquet")
        trades_df.to_parquet("artifacts/trades.parquet")
        try:
            self.store.write("history", hist_df)
            self.store.write("trades", trades_df)
        except Exception as e:
            print("DuckDB write failed (optional):", e)

        if return_dataframes:
            return hist_df, trades_df, notes, transcript
        return None

    def _merge_actions(self, acts: List[Dict], obs: Dict) -> List[Dict]:
        agg = {s: 0 for s in obs["symbols"].keys()}
        for a in acts:
            if a.get("action") == "buy":  agg[a["symbol"]] += 1
            elif a.get("action") == "sell": agg[a["symbol"]] -= 1
        merged = []
        for s, score in agg.items():
            if score > 0:
                merged.append({"action":"buy","symbol":s,"qty":10,"price":None,"reason":"merged"})
            elif score < 0:
                merged.append({"action":"sell","symbol":s,"qty":10,"price":None,"reason":"merged"})
            else:
                merged.append({"action":"hold","symbol":s,"qty":0,"price":None,"reason":"merged"})
        return merged

    def _apply_trades(self, trades: List[Trade]):
        st = self.cfg
        for t in trades:
            notional = t.price * t.qty
            fee = notional * st.fee_bps / 10_000.0
            if t.buy_agent == "exec":
                self._state.cash -= (notional + fee)
                self._state.positions[t.symbol] += t.qty
            if t.sell_agent == "exec":
                self._state.cash += (notional - fee)
                self._state.positions[t.symbol] -= t.qty
