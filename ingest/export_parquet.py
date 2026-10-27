"""Export dbt mart tables from DuckDB to Parquet files."""
from pathlib import Path

import duckdb

DB_PATH = "warehouse.duckdb"
OUT_DIR = Path("exports")
TABLES = ["fct_orders", "dim_customers"]


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        for table in TABLES:
            out = (OUT_DIR / f"{table}.parquet").as_posix()
            con.execute(f"COPY (SELECT * FROM {table}) TO '{out}' (FORMAT parquet, COMPRESSION zstd)")
            rows = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
            size_kb = (OUT_DIR / f"{table}.parquet").stat().st_size / 1024
            print(f"{table}: {rows} rows -> {out} ({size_kb:.1f} KB)")
    finally:
        con.close()


if __name__ == "__main__":
    main()