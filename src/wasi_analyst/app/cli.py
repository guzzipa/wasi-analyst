from typer import Typer, Option
from wasi_analyst.core.market import Market
from wasi_analyst.data.providers import RandomWalkProvider
from wasi_analyst.agents.coordinator import Coordinator
from wasi_analyst.util.store import DuckDBStore
from wasi_analyst.util.config import WasiConfig

app = Typer(help="Wasi Analyst CLI")

@app.command()
def hello():
    """Smoke test simple."""
    print("Wasi Analyst instalado ✅")

@app.command()
def simulate(
    days: int = Option(10, "--days", help="Trading days"),
    symbols: str = Option("AAPL,MSFT", "--symbols", help="Símbolos separados por coma"),
    seed: int = Option(123, "--seed", help="Random seed"),
):
    """Corre una simulación mínima y guarda artefactos."""
    cfg = WasiConfig(
        seed=seed,
        days=days,
        symbols=[s.strip() for s in symbols.split(",") if s.strip()],
    )
    market = Market(cfg, price_provider=RandomWalkProvider(seed=seed))
    store = DuckDBStore("wasi.duckdb")
    coord = Coordinator(cfg=cfg, market=market, store=store)
    coord.run()
    print("✅ Simulation complete. Artifacts en ./artifacts y ./wasi.duckdb (si DuckDB disponible)")
