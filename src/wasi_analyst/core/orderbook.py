from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Order:
    side: str                   # 'buy' or 'sell'
    symbol: str
    qty: int
    price: Optional[float]      # limit price or None for market
    agent_id: str

@dataclass
class Trade:
    symbol: str
    price: float
    qty: int
    buy_agent: str
    sell_agent: str

@dataclass
class Book:
    symbol: str
    bids: List[Order] = field(default_factory=list)  # sorted desc price
    asks: List[Order] = field(default_factory=list)  # sorted asc price

    def add(self, o: Order):
        if o.side == 'buy':
            self.bids.append(o)
            self.bids.sort(key=lambda x: (-(x.price or float('inf'))))
        else:
            self.asks.append(o)
            self.asks.sort(key=lambda x: ((x.price or 0)))

    def match(self) -> List[Trade]:
        trades: List[Trade] = []
        while self.bids and self.asks:
            b = self.bids[0]; a = self.asks[0]
            bp = b.price if b.price is not None else (a.price or 0)
            ap = a.price if a.price is not None else (b.price or 0)
            if bp >= ap:
                px = (ap if b.price is None else bp) if (a.price is None or b.price is None) else (ap + b.price) / 2
                qty = min(b.qty, a.qty)
                trades.append(Trade(symbol=b.symbol, price=px, qty=qty, buy_agent=b.agent_id, sell_agent=a.agent_id))
                b.qty -= qty; a.qty -= qty
                if b.qty == 0: self.bids.pop(0)
                if a.qty == 0: self.asks.pop(0)
            else:
                break
        return trades
