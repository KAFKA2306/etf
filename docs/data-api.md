# JPX ETF データ API v1

この配布層は、既存のノートブック・pickle・価格キャッシュを変更せず、日本取引所グループ（JPX）の公式ETF新規上場情報を機械利用可能な形式で提供します。

## 配布物

- `api/v1/manifest.json`: 件数、期間、出典、利用条件、各配布物のbyte数とSHA-256
- `api/v1/listings.json`: 上場日、コード、ファンド名、連動対象指標、管理会社、売買単位、信託報酬、iNAV、アクティブETF区分
- `api/v1/listings.csv`: 表計算・DB取込用
- `api/v1/facets.json`: 管理会社、上場月、アクティブETF、iNAVの集計

## 正準ソース

- JPX Listed Issues - ETFs: https://www.jpx.co.jp/english/equities/products/etfs/issues/index.html
- JPX Terms of Use: https://www.jpx.co.jp/english/terms-of-use/index.html

取得時点はsnapshotの`retrieved_at`に保存します。過去snapshotは削除せず、更新ごとに新しい取得日または対象期間のファイルを追加してください。

## 欠損値

`index_name = null`は、公式一覧で連動対象指標が`-`と表示されているアクティブETFを意味します。推定値では補完しません。

## 差分同期

最初に`manifest.json`を取得し、`distributions.*.sha256`が前回値と異なるファイルだけを再取得してください。

```python
import hashlib, json, urllib.request

base = "https://raw.githubusercontent.com/KAFKA2306/etf/main/api/v1/"
manifest = json.load(urllib.request.urlopen(base + "manifest.json"))
payload = urllib.request.urlopen(base + "listings.json").read()
assert hashlib.sha256(payload).hexdigest() == manifest["distributions"]["listings.json"]["sha256"]
```

## 互換性

v1では既存フィールドを削除しません。破壊的変更は`api/v2`へ分離します。既存の`chart.csv`、pickle、notebook、`fetch.py`はこのAPIの正準入力ではありません。
