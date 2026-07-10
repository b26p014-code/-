import csv
import time
from datetime import datetime
import random
import serial
import board
import adafruit_dht

# 1. adafruit config
dhtDevice = adafruit_dht.DHT22(board.D18)
# 保存するCSVファイル名
FILENAME = "temperature_log.csv"

try:
    # input() で受け取った文字列を float（小数点対応の数値）に変換
    user_input = input("計測間隔（分）を入力してください（例: 5 や 0.5）: ")
    INTERVAL_SEC_INPUT = float(user_input)
    
    if INTERVAL_SEC_INPUT <= 0:
        print("エラー: 0より大きい数値を入力してください。")
        exit()

    INTERVAL_SEC = INTERVAL_SEC_INPUT * 60.0

except ValueError:
    print("エラー: 正しい数値を入力してください。")
    exit()

# CSVファイルの初期設定（ヘッダーの書き込み）
with open(FILENAME, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    # 列の名前（タイムスタンプ、温度）
    writer.writerow(["Timestamp", "Temperature (°C)"])

print(f"{FILENAME} を作成しました。データ記録を開始します... (Ctrl+C で終了)")

try:
    while True:
        try:
            # 現在の時刻を取得
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # センサデータの代わりに20.0〜25.0度のランダムな数値を生成
            temperature = dhtDevice.temperature
            
            # CSVファイルに追記（mode='a'）
            with open(FILENAME, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([now, temperature])
                
            print(f"[{now}] 記録完了: {temperature} °C")
            
            # 入力した秒ごとにデータを取得
        except RuntimeError as error:
        # Errors happen fairly often, DHT's are hard to read, just keep going
            print(error.args[0])
            continue
            
        time.sleep(INTERVAL_SEC)

except KeyboardInterrupt:
    print("\n記録を停止しました。")
