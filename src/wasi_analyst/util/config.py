from pydantic import BaseModel, Field
from typing import List, Literal

AgentMode = Literal["rule", "llm"]

class WasiConfig(BaseModel):
    # Simulación
    days: int = 10
    symbols: List[str] = Field(default_factory=lambda: ["WASI"])
    seed: int = 123
    start_price: float = 100.0
    cash0: float = 100_000.0
    max_position_per_symbol: int = 200
    max_gross_exposure: float = 200_000.0
    fee_bps: float = 5.0
    slippage_bps: float = 10.0

    # Modos por agente
    fundamental_mode: AgentMode = "rule"
    macro_mode: AgentMode = "rule"
    sentiment_mode: AgentMode = "rule"

    # ---- Tuning de reglas (fallbacks) ----
    # Fundamental (mean-reversion)
    fundamental_sma_window: int = 5
    fundamental_base_thresh: float = 0.002  # 0.2% en fra.
    fundamental_qty_cap: int = 20

    # Macro (momentum)
    macro_mom_window: int = 3
    macro_thresh: float = 0.003  # 0.3%
    macro_qty_cap: int = 15

    # Sentiment (breakout)
    sentiment_break_window: int = 10
    sentiment_eps: float = 0.002  # 0.2%
    sentiment_qty: int = 8
