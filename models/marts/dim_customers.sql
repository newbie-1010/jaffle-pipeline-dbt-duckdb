with customers as (
    select * from {{ ref('stg_customers') }}
),
customer_orders as (
    select
        customer_id,
        min(order_date) as first_order,
        max(order_date) as most_recent_order,
        count(*) as number_of_orders,
        sum(amount) as lifetime_value
    from {{ ref('fct_orders') }}
    group by 1
)
select
    c.customer_id,
    c.first_name,
    c.last_name,
    co.first_order,
    co.most_recent_order,
    coalesce(co.number_of_orders, 0) as number_of_orders,
    coalesce(co.lifetime_value, 0) as customer_lifetime_value
from customers c
left join customer_orders co using (customer_id)