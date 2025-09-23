# Persistencia tolerante: si DuckDB no está instalado, no rompe el flujo.
from typing import Optional
import pandas as pd

class DuckDBStore:
    def __init__(self, path: str = "wasi.duckdb"):
        self.path = path
        try:
            import duckdb  # type: ignore
            self._db = duckdb.connect(path)
        except Exception:
            self._db = None  # modo no-op

    def write(self, table: str, df: pd.DataFrame):
        if self._db is None:
            return  # no-op
        self._db.execute(
            f"CREATE TABLE IF NOT EXISTS {table} AS SELECT * FROM df LIMIT 0"
        )
        self._db.execute(f"INSERT INTO {table} SELECT * FROM df")

    def close(self):
        if self._db is not None:
            self._db.close()
