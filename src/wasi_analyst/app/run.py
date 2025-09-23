from typing import List, Callable, Optional
from wasi_analyst.core.market import Market
from wasi_analyst.data.providers import RandomWalkProvider, YahooDailyReplay
from wasi_analyst.agents.coordinator import Coordinator
from wasi_analyst.util.config import WasiConfig
from wasi_analyst.util.store import DuckDBStore

ReportFn = Callable[[str, Optional[float]], None]

def run_simulation(
    days: int,
    symbols: List[str],
    seed: int,
    user_goal: str = "",
    data_source: str = "Random Walk",
    fundamental_mode: str = "rule",
    macro_mode: str = "rule",
    sentiment_mode: str = "rule",
    # ---- nuevos: tuning ----
    fundamental_sma_window: int = 5,
    fundamental_base_thresh: float = 0.002,
    fundamental_qty_cap: int = 20,
    macro_mom_window: int = 3,
    macro_thresh: float = 0.003,
    macro_qty_cap: int = 15,
    sentiment_break_window: int = 10,
    sentiment_eps: float = 0.002,
    sentiment_qty: int = 8,
    report: ReportFn = lambda msg, p=None: None,
) -> dict:
    total_steps = max(1, days * 4 + 4)
    step = 0
    def tick(msg: str):
        nonlocal step
        step += 1
        report(msg, min(0.999, step / total_steps))

    report("Inicializando configuración…", 0.02)
    cfg = WasiConfig(
        seed=seed, days=days, symbols=symbols,
        fundamental_mode=fundamental_mode, macro_mode=macro_mode, sentiment_mode=sentiment_mode,
        fundamental_sma_window=fundamental_sma_window,
        fundamental_base_thresh=fundamental_base_thresh,
        fundamental_qty_cap=fundamental_qty_cap,
        macro_mom_window=macro_mom_window,
        macro_thresh=macro_thresh,
        macro_qty_cap=macro_qty_cap,
        sentiment_break_window=sentiment_break_window,
        sentiment_eps=sentiment_eps,
        sentiment_qty=sentiment_qty,
    )

    tick(f"Seleccionando fuente de datos: {data_source}")
    price_provider = YahooDailyReplay(symbols) if data_source == "Yahoo Finance (daily)" else RandomWalkProvider(seed=seed)

    tick("Creando mercado y store…")
    market = Market(cfg, price_provider=price_provider)
    store = DuckDBStore("wasi.duckdb")
    coord = Coordinator(cfg=cfg, market=market, store=store)

    def loop_report(day: int, phase: str):
        report(f"Día {day+1}/{days} · {phase}", None)

    tick("Ejecutando simulación…")
    history_df, trades_df, notes, transcript = coord.run(
        return_dataframes=True, user_goal=user_goal, loop_report=loop_report
    )

    tick("Listo. Persistiendo…")
    report("Completado ✅", 1.0)
    return {"history": history_df, "trades": trades_df, "notes": notes, "transcript": transcript}
