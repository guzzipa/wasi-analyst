from __future__ import annotations
from typing import Dict, List
from .base import BaseAgent

class RiskManager(BaseAgent):
    def enforce(self, actions: List[dict], obs: Dict) -> List[dict]:
        capped: List[dict] = []
        prices = {k: v["price"] for k, v in obs["symbols"].items()}

        max_pos = int(getattr(self.cfg, "max_position_per_symbol", 100)) or 100
        max_gross = float(getattr(self.cfg, "max_gross_exposure", 1e12))

        for a in actions:
            if a.get("action") == "hold":
                capped.append(a); continue

            sym   = a["symbol"]
            side  = a["action"]
            price = float(prices[sym])
            qty   = int(a.get("qty", 0))
            pos   = int(self.state.positions.get(sym, 0))
            note  = []

            if qty <= 0:
                capped.append({**a, "qty": 0})
                continue

            if side == "buy":
                max_add = max(0, max_pos - pos)
                if max_add <= 0:
                    qty = 0; note.append("cap: max_position_per_symbol")
                else:
                    if qty > max_add:
                        qty = max_add; note.append(f"cap->max_pos({max_pos})")

                if qty > 0:
                    affordable = int(self.state.cash // price)
                    if affordable <= 0:
                        qty = 0; note.append("cap: no_cash")
                    elif qty > affordable:
                        qty = affordable; note.append("cap->cash")

                if qty > 0:
                    new_notional = qty * price
                    gross = self.gross_exposure(prices)
                    if (gross + new_notional) > max_gross:
                        leftover = max_gross - gross
                        fit_qty = int(max(0, leftover // price))
                        if fit_qty <= 0:
                            qty = 0; note.append("cap: gross_exposure")
                        elif fit_qty < qty:
                            qty = fit_qty; note.append("cap->gross")

            elif side == "sell":
                max_sell = max(0, pos)
                if max_sell <= 0:
                    qty = 0; note.append("cap: no_position")
                elif qty > max_sell:
                    qty = max_sell; note.append("cap->position")

            out = {**a, "qty": int(qty)}
            if note: out["risk_note"] = "; ".join(note)
            capped.append(out)

        return capped

    def gross_exposure(self, prices: Dict[str, float]) -> float:
        return sum(abs(q) * float(prices[sym]) for sym, q in self.state.positions.items())
