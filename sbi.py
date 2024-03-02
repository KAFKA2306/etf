import pandas as pd
import pickle

# ファイルパス
file_path = r'C:\Users\100ca\Documents\PyCode\etf\data\SBI-US-ETF.csv'

# CSVファイルを読み込む
df = pd.read_csv(file_path, encoding='utf-8-sig')

# データフレームを表示
print(df)

pkl_file_path = file_path.replace('.csv', '.pkl')
df.to_pickle(pkl_file_path)
print("データフレームをpkl形式で保存")


# "Ticker"列をリストに変換
ticker_list = df["Ticker"].to_list()

with open('tickers.pkl', 'wb') as f:
    pickle.dump(ticker_list, f)
print("リストをpickleファイルとして保存")

# 確認のために保存したリストを読み込む
with open('tickers.pkl', 'rb') as f:
    loaded_ticker_list = pickle.load(f)
#    print(loaded_ticker_list)
