from typing import Dict
from .base import BaseAgent
from wasi_analyst.util.schemas import Action
from .llm_mixins import llm_actions

class FundamentalAgent(BaseAgent):
    def decide(self, obs: Dict, user_goal: str = "") -> Dict:
        if self.mode == "llm":
            out = llm_actions("fundamental", obs, user_goal)
            return {"role": "fundamental", **out}

        cap = self.cfg.fundamental_qty_cap
        base = self.cfg.fundamental_base_thresh

        actions = []
        for sym, f in obs["symbols"].items():
            price, sma, vol = f["price"], f["sma"], max(1e-6, f.get("vol", 0.0))
            thresh = base + 0.5 * vol
            dev = (price / sma - 1.0) if sma > 0 else 0.0
            qty = min(cap, max(0, int(abs(dev) / (thresh + 1e-6) * 5)))
            if dev < -thresh:
                actions.append(Action(action="buy",  symbol=sym, qty=qty, price=None, reason="mean-reversion").model_dump())
            elif dev >  thresh:
                actions.append(Action(action="sell", symbol=sym, qty=qty, price=None, reason="mean-reversion").model_dump())
            else:
                actions.append(Action(action="hold", symbol=sym, qty=0, price=None, reason="near-sma").model_dump())
        return {"role": "fundamental", "reasoning": "rule-based mean-reversion", "actions": actions}
