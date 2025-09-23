from typing import Dict, List
from dataclasses import dataclass, field
from .orderbook import Book, Order, Trade
from wasi_analyst.util.config import WasiConfig

@dataclass
class Instrument:
    symbol: str
    price: float
    book: Book

@dataclass
class Market:
    cfg: WasiConfig
    price_provider: "PriceProvider"
    day: int = 0
    instruments: Dict[str, Instrument] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)

    def __post_init__(self):
        import random
        random.seed(self.cfg.seed)
        for s in self.cfg.symbols:
            self.instruments[s] = Instrument(symbol=s, price=self.cfg.start_price, book=Book(symbol=s))

    def step_prices(self):
        for _, ins in self.instruments.items():
            ins.price = self.price_provider.next_price(ins.symbol, ins.price, self.day)
        self.day += 1

    def place(self, order: Order):
        self.instruments[order.symbol].book.add(order)

    def match_all(self):
        todays: List[Trade] = []
        for _, ins in self.instruments.items():
            t = ins.book.match()
            if t:
                ins.price = t[-1].price
                todays.extend(t)
        self.trades.extend(todays)
        return todays

    def snapshot_prices(self):
        return {s: ins.price for s, ins in self.instruments.items()}

class PriceProvider:
    def next_price(self, symbol: str, last: float, day: int) -> float: ...

