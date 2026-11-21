---
okf_version: "0.3"
title: "ETFデータのParquetとdbt"
description: "ARKの正準スナップショットから検証済みの単一Parquetを生成し、GitHub上で効率的に配布する方法。"
tags:
  - etf/data
  - etf/analytics
---

# ETFデータのParquetとdbt

## 正本と派生データ

- 正本: `data/ark-holdings/YYYY-MM-DD/<fingerprint>.json`（訂正を含め追記保存）
- 変換: `analytics/ark_parquet/models/`（dbt-duckdbで列型、重複、欠損、日付を検証）
- 派生: `data/ark-views/holdings-latest.parquet`（ZSTD圧縮、最新時点の1ファイル）
- 配布記録: `data/ark-views/holdings-latest.manifest.json`（観測日、原本SHA-256、変換コードSHA-256、出典URL、件数、バイナリSHA-256）
- 公開: `https://kafka2306.github.io/etf/data/holdings-latest.parquet`（Pagesに配布された場合）

Parquetの1行は「1観測日 × 1ファンド × 1保有銘柄」。最新の6ファンドだけを含む。過去の訂正・原本は既存のJSONに残す。

**実測（2026-11-20観測分）**: 6ファンド・232行・9,030バイト。対応する原本スナップショットは78,609バイト。Parquetは保有銘柄の表示用列へ絞っているため、これは圧縮率ではなく配布バイト数の比較。GitHubへの反映は [Parquet派生データ](../data/ark-views/holdings-latest.manifest.json) のSHA-256で確認する。元ファイルが変わらなければ生成・コミットを省略する。

## 実行

```sh
python -m pip install -r requirements-ark-views.txt
python -m unittest -v tests.test_ark_parquet
python scripts/build_ark_parquet.py
```

新しい依存パッケージや日次ジョブは作らない。既存の「ARK ETF holdings」ワークフローが取得・検証・Parquet化・変更分のみコミットを一度に実行する。

## データを検証して読む

```python
import hashlib, json, duckdb
from pathlib import Path
p = Path("data/ark-views/holdings-latest.parquet")
m = json.loads(Path("data/ark-views/holdings-latest.manifest.json").read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest() == m["parquet_sha256"]
db = duckdb.connect()
print(db.execute("select fund, count(*), sum(weight_pct) from read_parquet(?) group by fund order by fund", [str(p)]).fetchall())
```

データはレコメンドやETF全市場の網羅データではない。利用者が持つ別のETFスクリーニングCSV、第三者の契約対象データ、非公開の口座情報はここにアップロードしない。

## GitHub保管効率

- 数百行を日付ごとに細分割すると小さいParquetが乱立するので、最新を1つにまとめる。
- 1MB超の生成ファイルはこのパイプラインでコミットを拒否する。巨大な履歴はGitHub Releasesやオブジェクトストレージへ移す。
- dbtのSQLと設定のみGitで履歴管理し、一時的なDuckDBファイル、dbtログ、`target/`は保存しない。
- バイナリの配布とブラウザ表示は別物。finBIは軽いCSV/JSON等の表示契約を介して参照し、ブラウザのParquetデコードを前提にしない。

## 参照仕様

- [dbt-duckdb external materialization](https://github.com/duckdb/dbt-duckdb#reading-and-writing-external-files)
- [DuckDB Parquet](https://duckdb.org/docs/stable/data/parquet/overview)
- [GitHub repository limits](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)

## 配布の合否

PagesのビルドはParquetとmanifestの両方を必須として、配布前にSHA-256・容量・原本SHAを検証する。1つでも欠ければデプロイしない。ファイルがGitHub mainにあることと公開URLでHTTP取得できることは別の事象なので、リリース確認では公開先も別途照合する。

変換スクリプト・dbt SQL/YAMLのいずれかが変更された場合は、原本に変更がなくても新しい変換版として生成・検証する。原本と変換版が同一なら不要な再変換を避ける。

### 日次更新と公開の連動

GitHub Actionsの`GITHUB_TOKEN`でコミットした更新は、別ワークフローの`push`を起動しない。ARK取得ジョブで原本またはParquetの変更がコミットされた場合だけ、同じ既存Pagesワークフローを`workflow_dispatch`で明示起動する。変更がない日は起動しない。

出典: [GitHub公式 GITHUB_TOKENとworkflow実行](https://docs.github.com/en/actions/concepts/security/github_token)。本番の合否はPagesがアップロードしたという記録ではなく、デプロイ後のHTTPでParquetとmanifestを再取得してSHA-256を比較する。
