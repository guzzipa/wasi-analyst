from __future__ import annotations
import random
from typing import Dict, List
import pandas as pd

# --------- Demo provider: precios sintéticos ----------
class RandomWalkProvider:
    def __init__(self, seed: int = 123, drift: float = 0.0005, vol: float = 0.02):
        random.seed(seed)
        self.drift = drift
        self.vol = vol

    def next_price(self, symbol: str, last: float, day: int) -> float:
        from random import gauss
        shock = gauss(self.drift, self.vol)
        return max(1.0, last * (1.0 + shock))


# --------- Market replay con datos reales (Yahoo Finance) ----------
class YahooDailyReplay:
    """
    Reproduce precios diarios usando yfinance.
    Carga una vez el histórico de Close por símbolo y avanza día a día.
    """
    def __init__(self, symbols: List[str], period: str = "2y", interval: str = "1d"):
        try:
            import yfinance as yf  # type: ignore
        except Exception as e:
            raise RuntimeError("Falta 'yfinance'. Instalalo con: pip install yfinance") from e

        from functools import lru_cache

        self.symbols = list(dict.fromkeys([s.upper() for s in symbols]))  # únicos, mantiene orden
        self._series: Dict[str, List[float]] = {}
        self._idx: int = 0

        @lru_cache(maxsize=8)
        def _dl(symbols_tuple, period, interval):
            return yf.download(
                list(symbols_tuple) if len(symbols_tuple) > 1 else list(symbols_tuple)[0],
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=True,
                progress=False,
            )

        data = _dl(tuple(self.symbols), period, interval)

        for s in self.symbols:
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    closes = data[s]["Close"]
                else:
                    closes = data["Close"]
                ser = pd.Series(closes, dtype=float).dropna()
                self._series[s] = ser.tolist()
            except Exception as e:
                print(f"[WARN] YahooDailyReplay: no pude cargar {s} ({e}) -> fallback 100.0")
                self._series[s] = [100.0]

        # largo máximo entre series (para no pasarnos de rango)
        self._max_len = max(len(v) for v in self._series.values()) if self._series else 1

    def next_price(self, symbol: str, last: float, day: int) -> float:
        seq = self._series.get(symbol)
        if not seq:
            return last
        i = min(self._idx, len(seq) - 1)
        px = float(seq[i])

        # Avanzamos el índice global al final del "ciclo" del día,
        # cuando atendimos al último símbolo (orden alfabético estable).
        if symbol == sorted(self.symbols)[-1]:
            if self._idx < self._max_len - 1:
                self._idx += 1
        return px
