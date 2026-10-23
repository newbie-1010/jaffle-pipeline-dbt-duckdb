from matplotlib.table import table

import duckdb
from pathlib import Path
import argparse
import hashlib

RAW_DIR = Path("data/raw")
DB_PATH = "warehouse.duckdb"
KEY = "id"

FILES = {
    "customers": "raw_customers.csv",
    "orders": "raw_orders.csv",
    "payments": "raw_payments.csv",
}

NOW_UTC = "(current_timestamp AT TIME ZONE 'UTC')"

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda:f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def setup(con, full_refresh:bool) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    if full_refresh:
        for table in FILES:
            con.execute(f"DROP TABLE IF EXISTS raw.{table}")
        con.execute("DROP TABLE IF EXISTS raw._ingest_log")
    con.execute("""
    CREATE TABLE IF NOT EXISTS raw._ingest_log (
        table_name VARCHAR,
        file_name VARCHAR,
        file_hash TEXT,
        rows_read BIGINT,
        rows_inserted BIGINT,
        rows_updated BIGINT,
        status VARCHAR,
        run_at TIMESTAMP
    )
    """)

def table_exists(con, table: str) -> bool:
    return con.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema='raw' AND table_name=?",
        [table],
    ).fetchone()[0] > 0


def write_log(con, table, filename, fhash, read, inserted, updated, status) -> None:
    con.execute(
    f"INSERT INTO raw._ingest_log VALUES (?, ?, ?, ?, ?, ?, ?, {NOW_UTC})",
    [table, filename, fhash, read, inserted, updated, status],
    )

def load_table(con, table: str, filename:str) -> None:
    path = (RAW_DIR / filename)
    current_hash = file_hash(path)
    exists = table_exists(con, table)

    last = con.execute(
        "SELECT file_hash FROM raw._ingest_log "
        "WHERE table_name=? AND status = 'loaded' "
        "ORDER BY run_at DESC LIMIT 1",
        [table],
    ).fetchone()
    if exists and last and last[0] == current_hash:
        write_log(con, table, filename, current_hash, 0, 0, 0, "skipped")
        print(f"{table}: no changes detected, skipping load")
        return

    con.execute(
    f"CREATE OR REPLACE TEMP TABLE incoming AS "
    f"SELECT DISTINCT * FROM read_csv('{path.as_posix()}', header = true)"
    )
    rows_read, distinct_ids = con.execute(
    f"SELECT count(*), count(DISTINCT {KEY}) FROM incoming"
    ).fetchone()
    assert rows_read > 0, f"{table}: file has no rows"
    assert rows_read == distinct_ids, f"{table}: duplicate {KEY} values in file"

    if not exists:
        con.execute(
        f"CREATE TABLE raw.{table} AS SELECT *, {NOW_UTC} AS _loaded_at FROM incoming"
        )
        write_log(con, table, filename, current_hash, rows_read, rows_read, 0, "loaded")
        print(f"{table}: first load, {rows_read} rows inserted")
        return

    con.execute(
        f"CREATE OR REPLACE TEMP TABLE changes AS "
        f"SELECT * FROM incoming "
        f"EXCEPT SELECT * EXCLUDE (_loaded_at) FROM raw.{table}"
        )
    n_changes = con.execute("SELECT count(*) FROM changes").fetchone()[0]
    updated = con.execute(
        f"SELECT count(*) FROM changes WHERE {KEY} IN (SELECT {KEY} FROM raw.{table})"
    ).fetchone()[0]
    inserted = n_changes - updated

    if n_changes:
        con.begin()
        try:
            con.execute(f"DELETE FROM raw.{table} WHERE {KEY} IN (SELECT {KEY} FROM changes)")
            con.execute(f"INSERT INTO raw.{table} SELECT *, {NOW_UTC} FROM changes")
            con.commit()

        except Exception:
            con.rollback()
            raise

    write_log(con, table, filename, current_hash, rows_read, inserted, updated, "loaded")
    print(f"{table}: {inserted} inserted, {updated} updated, {rows_read - n_changes} unchanged")

def main() -> None:
    parser = argparse.ArgumentParser(description= "Incrementally load CSVs into DuckDB")
    parser.add_argument("--full-refresh", action="store_true", help="drop raw tables and the ingest log, then reload everything")
    args = parser.parse_args()
    con = duckdb.connect(DB_PATH)
    try:
        setup(con, args.full_refresh)
        for table, filename in FILES.items():
            load_table(con, table, filename)
    finally:
        con.close()

if __name__=="__main__":
    main()