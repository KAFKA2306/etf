# etf — ARK ETF holdings

[![ARK ETF holdings](https://github.com/KAFKA2306/etf/actions/workflows/ark-holdings-source.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/ark-holdings-source.yml)
[![ETF daily prices](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/daily-prices.yml)
[![JPX ETF data integrity](https://github.com/KAFKA2306/etf/actions/workflows/jpx-data.yml/badge.svg)](https://github.com/KAFKA2306/etf/actions/workflows/jpx-data.yml)

ARKの公開holdingsを時点付きで保存し、銘柄追加・削除・weight変化とfund間overlapを再生成できるようにするrepositoryです。

正準責務は `ark-etf-holdings` へのrename後も同じです。ARK Big Ideasのtheme mappingはholdings原本へ混ぜず、derived viewとして扱います。

## ARK公式holdings

対象:

- ARKK
- ARKQ
- ARKW
- ARKG
- ARKF
- ARKX

一次情報:

- https://www.ark-funds.com/our-etfs
- https://helpcenter.ark-funds.com/where-can-i-download-the-latest-etf-holdings
- https://helpcenter.ark-funds.com/can-you-explain-the-date-listed-on-the-ark-etf-holdings-documents

ARK公式はholdingsを各取引日の終了時に更新し、holdings文書の日付は次の取引日を示すと説明しています。そのため `as_of` と `retrieved_at` を分離して保持します。

## 正準データ

日次snapshot:

```text
data/ark-holdings/YYYY-MM-DD/<source-fingerprint>.json
```

各snapshotは次を保持します。

- fund ticker
- as-of
- retrieved_at
- official CSV URL
- official CSV SHA-256
- holdings rows

保存先はcontent-addressedです。同一as-ofで公式CSVの内容が同じ場合は重複snapshotを作らず、同一as-ofでも公式CSVが改訂された場合は別fingerprintとして追加します。既存snapshotは上書きしません。

## Derived views

- [`data/ark-views/latest.json`](data/ark-views/latest.json): 最新snapshotとsource metadata
- [`data/ark-views/changes.json`](data/ark-views/changes.json): 前回比の追加・削除・weight変化
- [`data/ark-views/overlap.json`](data/ark-views/overlap.json): 複数fundに共通するholding

再生成:

```bash
python build_ark_views.py
```

raw snapshotから決定的に再生成します。

## 自動取得

[`ARK ETF holdings`](https://github.com/KAFKA2306/etf/actions/workflows/ark-holdings-source.yml) は米国取引日の終了後を狙って火曜〜土曜 10:30 UTCに実行します。

処理:

```text
official ARK CSV
  -> fund identity / as-of validation
  -> append-only snapshot
  -> changes / overlap rebuild
  -> changed files only commit
```

同じ公式CSVを再取得しただけならcommitしません。6 fundのas-ofが一致しない場合は保存せず失敗します。

## 検証

```bash
python -m unittest -v test_ark_holdings.py
python collect_ark_holdings.py --output-dir /tmp/ark-holdings
```

unit testsはparser、現行ARKX file名、append-only保存、changes/overlap再生成を検証します。Pull Requestではさらに6 fundの公式CSVを実取得してsource driftを検出します。

## 60 trading days

ARK公式サイトで確認できるのは最新の日次holdingsで、過去60取引日分の日次archiveは正準sourceとして利用できません。このため第三者archiveで埋めず、workflowで今後のsnapshotを蓄積します。60 trading days到達まではIssue #9を閉じません。

## 既存ETF比較データ

ARK holdingsとは別系統として、既存のETF価格snapshotとJPX公式listing snapshotも現在のrepositoryに残っています。

- [`data/prices/current.json`](data/prices/current.json)
- [`api/v1/manifest.json`](api/v1/manifest.json)
- [`api/v1/listings.json`](api/v1/listings.json)

repository rename / 責務整理は `KAFKA2306/investor2#110` で扱います。ARK holdingsのfact生成ではこれらを参照しません。

## 注意

本repositoryは観測データと再現可能なderived viewを提供します。ARKの投資テーマ・将来予測・推奨をholdings factとして保存しません。
