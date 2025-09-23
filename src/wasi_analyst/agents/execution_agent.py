from .base import BaseAgent
from typing import List
from wasi_analyst.core.orderbook import Order

class ExecutionAgent(BaseAgent):
    def to_orders(self, actions: List[dict]) -> List[Order]:
        orders = []
        for a in actions:
            side = a["action"]
            if side not in ("buy", "sell"):
                continue
            orders.append(Order(
                side=side,
                symbol=a["symbol"],
                qty=int(a["qty"]),
                price=a.get("price", None),
                agent_id=self.agent_id
            ))
        return orders
