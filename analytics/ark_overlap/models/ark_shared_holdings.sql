{{ config(materialized='table') }}

select security, list(fund order by fund) as funds, count(*) as fund_count
from {{ ref('ark_fund_securities') }}
group by security
having count(*) > 1
