import duckdb
from pathlib import Path

RAW_DIR = Path("data/raw")
DB_PATH = "warehouse.duckdb"

FILES = {
    "customers": "raw_customers.csv",
    "orders": "raw_orders.csv",
    "payments": "raw_payments.csv",
}

def load_table(con, table, filename):
    path = (RAW_DIR / filename).as_posix()

    con.execute(f"""
    CREATE OR REPLACE TABLE raw.{table} AS
    SELECT *, current_timestamp AS _loaded_at
    FROM (SELECT DISTINCT * FROM read_csv('{path}', header=true))    
    """)

    total, distinct_ids = con.execute(
        f"SELECT count(*), count(DISTINCT id) FROM raw.{table}"
    ).fetchone()
    assert total > 0, f"{table}: no rows loaded"
    assert total == distinct_ids, f"{table}: duplicate ids found"
    print(f"Loaded raw.{table}: {total} rows")

def main():
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table, filename in FILES.items():
        load_table(con, table, filename)

    con.close()

if __name__=="__main__":
    main()