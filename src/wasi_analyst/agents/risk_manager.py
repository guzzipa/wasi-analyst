from .base import BaseAgent
from typing import Dict

class RiskManager(BaseAgent):
    def enforce(self, actions, obs: Dict):
        capped = []
        prices = {k:v["price"] for k,v in obs["symbols"].items()}
        for a in actions:
            if a["action"] == "hold":
                capped.append(a); continue
            sym = a["symbol"]; price = prices[sym]; qty = int(a["qty"])
            pos = int(self.state.positions.get(sym, 0))

            if a["action"] == "buy":
                max_add = max(0, self.cfg.max_position_per_symbol - pos)
                notional = min(max_add, qty) * price
                if (notional + self.gross_exposure(prices)) > self.cfg.max_gross_exposure:
                    qty = 0
                else:
                    qty = min(qty, max_add)
            elif a["action"] == "sell":
                qty = min(qty, max(0, pos))

            capped.append({**a, "qty": int(qty)})
        return capped

    def gross_exposure(self, prices):
        return sum(abs(q) * prices[sym] for sym, q in self.state.positions.items())
