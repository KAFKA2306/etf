# ETFデータ分析

このプロジェクトは、ETF（上場投資信託）のデータを分析するためのPythonスクリプトとJupyter Notebookを含んでいます。主な目的は、各ETFのシャープレシオを計算し、それに基づいてETFをランキングすることです。

## ファイルの概要

- `etf/code/top.ipynb`: メインのJupyter Notebookファイル。ここでデータのロード、シャープレシオの計算、ETFの株価のプロットなどが行われます。
- `etf/data/etf_weekly_close_cache.pkl`: ETFの週次終値データがキャッシュされたPickleファイル。
- `etf/data/etf_weekly_close.csv`: ETFの週次終値データが保存されたCSVファイル。

## 使用方法

1. `etf/data/etf_weekly_close_cache.pkl`にETFの週次終値データをキャッシュします。データはPythonのPickle形式で保存します。
2. `etf/code/top.ipynb`を開き、必要なライブラリをインポートします。
3. `load_cache`関数を使用してキャッシュされたデータをロードします。
4. `calculate_sharpe_ratios`関数を使用して各ETFのシャープレシオを計算し、それに基づいてETFをランキングします。
5. `etf_prices`関数を使用してシャープレシオ順にETFの株価をプロットし、それを4つのsubplotに分割して表示します。

## 注意事項

- このプロジェクトは、Python 3.6以上と以下のライブラリが必要です：pandas, numpy, pickle, matplotlib, plotly, IPython.display。
- ETFの週次終値データは、各ETFの終値を週ごとに集計したものである必要があります。
- シャープレシオの計算では、無リスクレートを0と仮定しています。無リスクレートが異なる場合は、適切に修正する必要があります。
