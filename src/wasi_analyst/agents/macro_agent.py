from typing import Dict
from .base import BaseAgent
from wasi_analyst.util.schemas import Action
from .llm_mixins import llm_actions

class MacroAgent(BaseAgent):
    def decide(self, obs: Dict, user_goal: str = "") -> Dict:
        if self.mode == "llm":
            out = llm_actions("macro", obs, user_goal)
            return {"role":"macro", **out}

        cap = self.cfg.macro_qty_cap
        thresh = self.cfg.macro_thresh

        actions = []
        for sym, f in obs["symbols"].items():
            mom = f.get("mom", 0.0)
            qty = min(cap, max(0, int(abs(mom) / (thresh + 1e-6) * 4)))
            if mom >  thresh:
                actions.append(Action(action="buy",  symbol=sym, qty=qty, price=None, reason="momentum-up").model_dump())
            elif mom < -thresh:
                actions.append(Action(action="sell", symbol=sym, qty=qty, price=None, reason="momentum-down").model_dump())
            else:
                actions.append(Action(action="hold", symbol=sym, qty=0, price=None, reason="momentum-flat").model_dump())
        return {"role":"macro","reasoning":"rule-based momentum","actions":actions}
