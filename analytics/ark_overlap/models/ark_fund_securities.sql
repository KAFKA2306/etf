{{ config(materialized='ephemeral') }}

select fund, security
from {{ source('ark_latest', 'holdings') }}
