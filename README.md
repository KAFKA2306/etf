# etf — ETF比較

[![ETF daily prices](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml)
[![JPX ETF data integrity](https://github.com/KAFKA2306/etf/actions/workflows/jpx-data.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/jpx-data.yml)
[![ETF price fetch safety](https://github.com/KAFKA2306/etf/actions/workflows/price-fetch-safety.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/price-fetch-safety.yml)

**ETFは、値上がり率だけを並べても同じ条件の比較にはならない。**

同じ期間に見えても、配当を再投資しているか、通貨が同じか、為替ヘッジがあるか、調整済み価格か、設定日前のデータが混ざっていないかで結果は変わります。過去snapshotを最新データのように扱えば、計算自体が正しくても比較の意味を誤ります。

このrepositoryは、週次価格データを使ってETFの収益とリスクを比較し、その前提条件を確認する研究用プロジェクトです。リターン、volatility、Sharpe ratio、JPX公式snapshotを扱います。

**リポジトリ:** https://github.com/KAFKA2306/etf

現在のコードと価格データは研究用の過去スナップショットです。最新のETF、価格、経費率、指数構成、為替ヘッジ条件を自動的に保証するものではありません。

## JPX公式ETFデータ API v1

既存分析とは分離して、日本取引所グループ（JPX）の公式ETF新規上場情報を検証済みsnapshotから配布します。

- `api/v1/manifest.json`: 件数、対象期間、出典、利用条件、SHA-256
- `api/v1/listings.json`: JSON配布
- `api/v1/listings.csv`: CSV配布
- `api/v1/facets.json`: 管理会社・上場月・アクティブETF・iNAV集計
- `docs/data-api.md`: データ辞書、欠損値、差分同期、互換性

正準snapshotは`data/official/`に保持し、過去snapshotを削除せず履歴として追加します。通常CIは外部サイトへアクセスせず、保存済みsnapshotから決定的に配布物を再生成します。

## 主な分析

- 週次価格の読込
- 週次リターンの計算
- 平均リターンとボラティリティ
- シャープレシオ
- ETF間ランキング
- Matplotlib・Plotlyによる可視化

## 入力データ

ETFごとの週次終値または調整済み終値を想定します。

分析前に次を確認してください。

- 価格が配当・分割調整済みか
- 通貨が統一されているか
- 為替ヘッジ有無
- 休場週・欠損週の扱い
- ETFの設定日より前のデータが混入していないか
- 上場廃止ETFを除外していないか

## シャープレシオ

```text
Sharpe ratio
= (平均リターン − 無リスク利回り) / リターン標準偏差
```

既存実装では無リスク利回りを0と置く場合があります。分析期間や通貨に応じた短期金利を使う場合は、週次単位へ変換し、価格データと期間をそろえてください。

## 必要ライブラリ

主な利用ライブラリ:

```text
pandas
numpy
matplotlib
plotly
IPython
```

`pickle`はPython標準ライブラリです。信頼できないpickleファイルを読み込むと任意コード実行の危険があるため、外部から受け取ったファイルを開かないでください。

## 実行方法

リポジトリ内のNotebookまたはPythonスクリプトを、隔離した仮想環境から実行します。

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas numpy matplotlib plotly jupyter
jupyter lab
```

公式JPX API配布物だけを再生成・検証する場合は外部ライブラリ不要です。

```bash
python scripts/build_jpx_api.py
python -m unittest discover -s tests -v
```

Windowsでは仮想環境の有効化コマンドを環境に合わせて変更してください。

## 比較時の注意

- シャープレシオだけで商品を選ばない
- 期間の開始・終了をそろえる
- 分配金再投資の有無をそろえる
- 経費率、売買手数料、スプレッド、税を考慮する
- レバレッジ型・インバース型を通常ETFと同じ前提で比較しない
- 小標本のランキングを安定した能力と解釈しない
- 過去の上位ETFだけを抽出する選択バイアスに注意する

## 改修優先度

- `pyproject.toml`とロックファイルを追加する
- 価格入力データのスキーマを明示する
- 無リスク金利を設定可能にする
- 調整済み価格と分配金を検証する
- ウォークフォワード評価を追加する
- 結果へ対象期間とデータ取得日を表示する

## 注意

本プロジェクトはETF分析の学習・研究用です。投資助言、商品推奨、将来収益の保証ではありません。
