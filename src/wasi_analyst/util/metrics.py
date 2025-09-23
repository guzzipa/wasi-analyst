from __future__ import annotations
import math
import numpy as np
import pandas as pd

ANNUALIZATION = 252  # días bursátiles aprox.

def period_return(prices: pd.Series) -> float:
    prices = prices.dropna()
    if len(prices) < 2:
        return float("nan")
    return float(prices.iloc[-1] / prices.iloc[0] - 1.0)

def cagr(prices: pd.Series, periods_per_year: int = ANNUALIZATION) -> float:
    prices = prices.dropna()
    n = len(prices)
    if n < 2 or prices.iloc[0] <= 0:
        return float("nan")
    total = prices.iloc[-1] / prices.iloc[0]
    years = n / periods_per_year
    if years <= 0:
        return float("nan")
    return float(total ** (1.0 / years) - 1.0)

def sharpe(prices: pd.Series, rf: float = 0.0, periods_per_year: int = ANNUALIZATION) -> float:
    rets = prices.dropna().pct_change().dropna()
    if len(rets) == 0:
        return float("nan")
    excess = rets - rf / periods_per_year
    mu = excess.mean()
    sd = excess.std(ddof=1)
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float((mu / sd) * math.sqrt(periods_per_year))

def max_drawdown(prices: pd.Series) -> float:
    p = prices.dropna()
    if p.empty:
        return float("nan")
    roll_max = p.cummax()
    dd = p / roll_max - 1.0
    return float(dd.min())

def equity_metrics(equity: pd.Series) -> dict:
    return {
        "period_return": period_return(equity),
        "cagr": cagr(equity),
        "sharpe": sharpe(equity),
        "max_drawdown": max_drawdown(equity),
    }

def price_metrics_table(hist: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in hist.columns if c.startswith("px_")]
    rows = []
    for c in cols:
        sym = c.replace("px_", "")
        s = hist[c]
        rows.append({
            "symbol": sym,
            "period_return": period_return(s),
            "cagr": cagr(s),
            "sharpe": sharpe(s),
            "max_drawdown": max_drawdown(s),
        })
    return pd.DataFrame(rows).set_index("symbol").sort_index()
