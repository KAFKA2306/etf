{{ config(materialized='ephemeral') }}
-- Normalize only the existing ARK snapshot; do not invent tickers or missing values.
select
    cast(as_of as date) as as_of,
    fund,
    security,
    nullif(ticker, '') as ticker,
    company,
    cast(shares as bigint) as shares,
    cast(market_value_usd as decimal(20, 2)) as market_value_usd,
    cast(weight_pct as decimal(9, 4)) as weight_pct,
    source_sha256,
    source_csv_url
from {{ source('ark_snapshot', 'holdings') }}
