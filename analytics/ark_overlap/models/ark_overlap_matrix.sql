{{ config(materialized='table') }}

with holdings as (
    select fund, security from {{ ref('ark_fund_securities') }}
),
funds as (
    select fund from {{ source('ark_latest', 'funds') }}
),
counts as (
    select a.fund as left_fund, b.fund as right_fund, count(*) as shared_count
    from holdings as a
    inner join holdings as b on a.security = b.security
    group by a.fund, b.fund
)
select
    a.fund as left_fund,
    b.fund as right_fund,
    coalesce(counts.shared_count, 0) as shared_count
from funds as a
cross join funds as b
left join counts on a.fund = counts.left_fund and b.fund = counts.right_fund
