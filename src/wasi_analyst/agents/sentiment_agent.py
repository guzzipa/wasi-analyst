from typing import Dict
from .base import BaseAgent
from wasi_analyst.util.schemas import Action
from .llm_mixins import llm_actions

class SentimentAgent(BaseAgent):
    def decide(self, obs: Dict, user_goal: str = "") -> Dict:
        if self.mode == "llm":
            out = llm_actions("sentiment", obs, user_goal)
            return {"role":"sentiment", **out}

        eps = self.cfg.sentiment_eps
        qty = self.cfg.sentiment_qty

        actions = []
        for sym, f in obs["symbols"].items():
            p, hi, lo = f["price"], f.get("hi", p), f.get("lo", p)
            if p >= hi * (1 + eps):
                actions.append(Action(action="buy",  symbol=sym, qty=qty, price=None, reason="breakout-high").model_dump())
            elif p <= lo * (1 - eps):
                actions.append(Action(action="sell", symbol=sym, qty=qty, price=None, reason="breakout-low").model_dump())
            else:
                actions.append(Action(action="hold", symbol=sym, qty=0, price=None, reason="range").model_dump())
        return {"role":"sentiment","reasoning":"rule-based breakout","actions":actions}
