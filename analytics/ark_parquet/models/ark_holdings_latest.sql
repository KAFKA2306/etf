{{
    config(
        materialized='external',
        location=env_var('ARK_PARQUET_OUT'),
        format='parquet',
        options={'compression': 'zstd', 'row_group_size': 100000}
    )
}}
-- Single, latest, compressed file: no per-day partitions for ~200 rows.
select
    as_of, fund, security, ticker, company, shares,
    market_value_usd, weight_pct, source_sha256, source_csv_url
from {{ ref('stg_ark_holdings') }}
order by fund, weight_pct desc, security
