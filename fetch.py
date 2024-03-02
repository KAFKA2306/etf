import yfinance as yf
import pandas as pd
import datetime
import os
import pickle 

# ETFのティッカーリスト
etfs = ["FEPI", "PSI", "SHOC", "FTXL", "CHPS", "EMSF", "SOXQ", "SOXX", "SMH", "SEMI", "FFND", "IGPT", "XSD", "ARVR", "LOUP", "XNTK"]
# 確認のために保存したリストを読み込む

with open(r'C:\Users\100ca\Documents\PyCode\etf\code\tickers.pkl', 'rb') as file:
    etfs = pickle.load(file)

# キャッシュファイルのパスをpickle用に変更
cache_path = fr"C:\Users\100ca\Documents\PyCode\etf\data\etf_weekly_close_cache.pkl"

def load_cache():
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as file:  # Changed to binary read mode
            return pickle.load(file)
    return {}

def save_cache(cache):
    with open(cache_path, "wb") as file:  # Changed to binary write mode
        pickle.dump(cache, file)

def get_last_friday():
    today = datetime.date.today()
    last_friday = today - datetime.timedelta(days=(today.weekday() + 3) % 7)
    return last_friday

def fetch_weekly_close(etf):
    # 5年前の日付を計算
    start_date = (datetime.date.today() - datetime.timedelta(days=5*365)).strftime("%Y-%m-%d")
    # 現在の日付
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    
    data = yf.download(etf, start=start_date, end=end_date, interval="1wk")
    # 終値と日付の列を返す
    return data["Close"].reset_index()

def update_weekly_closes(etfs):
    cache = load_cache()
    for etf in etfs:
        try:
            data = fetch_weekly_close(etf)
            # 日付と終値をリストとして保存
            cache[etf] = data.to_dict('records')
        except Exception as e:
            print(f"Error fetching data for {etf}: {e}")
    
    save_cache(cache)
    return cache

# 更新して結果を表示
updated_closes = update_weekly_closes(etfs)
print(updated_closes)
