import duckdb

print(duckdb.sql("""
    select status, count(*) as orders, sum(amount) as revenue
    from 'exports/fct_orders.parquet'
    group by status
"""))

print(duckdb.sql("""
    select d.first_name, f.amount
    from 'exports/fct_orders.parquet' f
    join 'exports/dim_customers.parquet' d using (customer_id)
    order by f.amount desc
    limit 5
"""))

print(duckdb.sql("select name, type from parquet_schema('exports/fct_orders.parquet')"))