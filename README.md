# etf — ETF比較

[![ETF daily prices](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml)
[![JPX ETF data integrity](https://github.com/KAFKA2306/etf/actions/workflows/jpx-data.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/jpx-data.yml)
[![ETF price fetch safety](https://github.com/KAFKA2306/etf/actions/workflows/price-fetch-safety.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/price-fetch-safety.yml)

**ETFは、値上がり率だけを並べても同じ条件の比較にはならない。**

同じ期間に見えても、配当を再投資しているか、通貨が同じか、為替ヘッジがあるか、調整済み価格か、設定日前のデータが混ざっていないかで結果は変わります。

このrepositoryは、ETF価格を日々取得して取得日時とともに保存し、そのデータを研究用の比較に使うプロジェクトです。価格取得とJPX公式listing snapshotは別のデータ系統として扱います。

**リポジトリ:** https://github.com/KAFKA2306/etf

## 日次価格snapshot

最新の取得結果:

- データ: [`data/prices/current.json`](data/prices/current.json)
- 対象ticker: [`data/ticker-universe.json`](data/ticker-universe.json)
- 自動取得: [ETF daily prices](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml)
- 取得コード: [`fetch.py`](fetch.py)

`data/prices/current.json` には、provider、取得区間、`retrieved_at`、各tickerの実データ期間、row count、価格の意味、snapshot SHA-256を保存します。現在の取得粒度は日足 (`1d`) で、価格列は `raw_close` です。

GitHub Actionsは毎日08:17 Asia/Tokyoに取得します。価格が休日などで前回と同じでも、取得成功時は `retrieved_at` が更新されるため、収集処理が継続していることをGit履歴から確認できます。一部tickerの取得に失敗した場合は、成功分だけで最新snapshotを置き換えません。

価格取得には `yfinance` を使用しています。これはYahoo Financeの公式サービスではありません。公開データの利用条件はyfinanceおよびYahooの案内を確認してください。

## JPX公式ETFデータ API v1

価格取得とは分離して、日本取引所グループ（JPX）の公式ETF新規上場情報を検証済みsnapshotから配布します。

- `api/v1/manifest.json`: 件数、対象期間、出典、利用条件、SHA-256
- `api/v1/listings.json`: JSON配布
- `api/v1/listings.csv`: CSV配布
- `api/v1/facets.json`: 管理会社・上場月・アクティブETF・iNAV集計
- `docs/data-api.md`: データ辞書、欠損値、差分同期、互換性

正準snapshotは `data/official/` に保持し、過去snapshotを削除せず履歴として追加します。通常CIは外部サイトへアクセスせず、保存済みsnapshotから配布物を再生成します。

## 研究用の比較

既存Notebookでは、取得済み価格を使って次のような比較を行います。

- リターン
- 平均リターンとボラティリティ
- Sharpe ratio
- ETF間比較
- Matplotlib・Plotlyによる可視化

Notebookには週次へ集約して分析する既存コードも残っています。日次取得snapshotと分析時の集約粒度は区別してください。

## 比較前に確認すること

- `raw_close` か調整済み価格か
- 配当・分割をどう扱うか
- 通貨が同じか
- 為替ヘッジ有無
- 休場日・欠損日の扱い
- ETFの設定日より前のデータが混入していないか
- 上場廃止ETFを除外していないか
- 比較期間の開始・終了がそろっているか

## Sharpe ratio

```text
Sharpe ratio
= (平均リターン − 無リスク利回り) / リターン標準偏差
```

無リスク利回りを0と置く分析は、その前提を明示してください。異なる通貨・期間のETFを同じSharpe ratioだけで順位付けしないでください。

## 比較時の注意

- 経費率、売買手数料、スプレッド、税を無視しない
- レバレッジ型・インバース型を通常ETFと同じ前提で比較しない
- 小標本のランキングを安定した能力と解釈しない
- 過去の上位ETFだけを抽出する選択バイアスに注意する
- Sharpe ratioだけで商品を選ばない

## 価格を手動取得する

```bash
python -m pip install yfinance==1.5.2
python fetch.py --start 2024-01-01 --end 2026-08-17
```

`--end` は実行したい日付へ置き換えます。正常終了すると `data/prices/current.json` がatomicに置き換わります。

offline safety tests:

```bash
python -m unittest discover -s tests -p 'test_fetch_safety.py' -v
```

JPX配布物の再生成・検証:

```bash
python scripts/build_jpx_api.py
python -m unittest discover -s tests -v
```

## 注意

本プロジェクトはETF分析の学習・研究用です。投資助言、商品推奨、将来収益の保証ではありません。価格snapshotの `retrieved_at` と各seriesの `actual_end` を確認してから利用してください。
