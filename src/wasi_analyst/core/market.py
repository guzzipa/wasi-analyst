from __future__ import annotations
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

    # >>> NUEVO: acumulamos ejecuciones “LP” del día
    lp_trades_today: List[Trade] = field(default_factory=list)

    def __post_init__(self):
        import random
        random.seed(self.cfg.seed)
        for s in self.cfg.symbols:
            self.instruments[s] = Instrument(symbol=s, price=self.cfg.start_price, book=Book(symbol=s))

    # ---------- pricing ----------

    def step_prices(self):
        for _, ins in self.instruments.items():
            ins.price = self.price_provider.next_price(ins.symbol, ins.price, self.day)
        self.day += 1

    # ---------- execution ----------

    def place(self, order: Order):
        """
        Híbrido: mandamos al libro + ejecutamos inmediato contra un LP virtual
        para garantizar fills (qty>0). Los trades LP se guardan en un buffer
        diario para ser devueltos por match_all().
        """
        ins = self.instruments[order.symbol]
        ins.book.add(order)

        if order.qty <= 0:
            return

        slip = float(getattr(self.cfg, "slippage_bps", 10.0)) / 10_000.0
        last = float(ins.price)

        if order.side == "buy":
            px = last * (1.0 + slip)
            t = Trade(symbol=order.symbol, price=px, qty=order.qty,
                      buy_agent=order.agent_id, sell_agent="lp")
        elif order.side == "sell":
            px = last * (1.0 - slip)
            t = Trade(symbol=order.symbol, price=px, qty=order.qty,
                      buy_agent="lp", sell_agent=order.agent_id)
        else:
            return

        # Actualizamos precio y guardamos el fill para este “día”
        ins.price = px
        self.lp_trades_today.append(t)

    def match_all(self):
        """
        Devuelve TODOS los trades del día:
          - primero los del LP acumulados en place()
          - luego los del libro si existieran
        Limpia el buffer diario y persiste en self.trades.
        """
        todays: List[Trade] = []

        # 1) LP fills de hoy
        if self.lp_trades_today:
            todays.extend(self.lp_trades_today)
            self.lp_trades_today = []

        # 2) Matching del libro
        for _, ins in self.instruments.items():
            t = ins.book.match()
            if t:
                ins.price = t[-1].price
                todays.extend(t)

        # Persistimos y devolvemos
        self.trades.extend(todays)
        return todays

    # ---------- views ----------

    def snapshot_prices(self):
        return {s: ins.price for s, ins in self.instruments.items()}

class PriceProvider:
    def next_price(self, symbol: str, last: float, day: int) -> float: ...
