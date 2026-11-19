---
type: "Metric"
title: "保有銘柄の重なり"
description: "ARK ETFの共有銘柄一覧とファンド別の重なり行列を定義します。"
tags:
  - ETF
  - ARK
  - overlap
sources:
  - id: "ark-funds"
    resource: "https://www.ark-funds.com/our-etfs"
    title: "ARK公式のETFと保有銘柄"
  - id: "holdings-source"
    resource: "/models/sources.yml"
    title: "dbtの入力定義"
  - id: "shared-model"
    resource: "/models/ark_shared_holdings.sql"
    title: "共有銘柄モデル"
  - id: "matrix-model"
    resource: "/models/ark_overlap_matrix.sql"
    title: "重なり行列モデル"
generated:
  by: "codex/gpt-6"
  at: "2026-11-19T11:04:32Z"
---

# 保有銘柄の重なり

ARK公式の保有銘柄データを保存した最新スナップショットから、複数のファンドが保有する銘柄と、ファンド同士で重なる銘柄数を集計します。入力はファンドと銘柄IDの組につき1行です。[^ark-funds][^holdings-source]

- [共有銘柄一覧](models/ark_shared_holdings.sql)は、複数ファンドに共通する銘柄につき1行を返します。[^shared-model]
- [重なり行列](models/ark_overlap_matrix.sql)は、6本の対象ファンドの組につき1行を返します。重なりは銘柄数で表し、共通銘柄がなければ0、対角セルはそのファンドの銘柄数です。[^matrix-model]

リポジトリのルートで `python build_ark_views.py` を実行すると、一時DuckDBで `dbt build` が走り、集計結果を `data/ark-views/overlap.json` に出力します。

[^ark-funds]: ARK公式のETF一覧。
[^holdings-source]: dbtが参照する正規化済み入力。
[^shared-model]: 銘柄ごとにファンドを数え、2本以上の行を残します。
[^matrix-model]: 共通の銘柄IDでファンドの組を数えます。
