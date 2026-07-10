import csv
import time
from datetime import datetime
import serial

# シリアルポートの設定
BAUD_RATE = 9600
FILENAME = "sensor_data.csv"

print("=== 温度センサ記録システム初期設定 ===")

# 1. シリアルポートの入力
SERIAL_PORT = input("使用するシリアルポート名を入力してください (例: COM3, /dev/ttyUSB0): ").strip()

# ==================== 標準入力の取得 ====================
try:
    user_input = input("データ記録の間隔（分）を入力してください（例: 10）: ")
    INTERVAL_SEC_INPUT = float(user_input)
    
    if INTERVAL_SEC_INPUT <= 0:
        print("エラー: 0より大きい数値を入力してください。")
        exit()

    INTERVAL_SEC = INTERVAL_SEC_INPUT * 60

except ValueError:
    print("エラー: 正しい数値を入力してください。")
    exit()
# =======================================================

# CSVファイルの初期設定
with open(FILENAME, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["Timestamp", "Temperature (°C)"])

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # 通信安定化待ち
    print(f"\n{SERIAL_PORT} に接続しました。")
    print(f"{INTERVAL_SEC}秒ごとにデータを記録します...")

    last_recorded_time = 0

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode("utf-8").strip()
            current_time = time.time()
            
            # 入力された INTERVAL_SEC を使って判定
            if current_time - last_recorded_time >= INTERVAL_SEC:
                if line:
                    try:
                        temperature = float(line)
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        with open(FILENAME, mode="a", newline="", encoding="utf-8") as file:
                            writer = csv.writer(file)
                            writer.writerow([now, temperature])
                            
                        print(f"[{now}] センサ値: {temperature} °C")
                        
                        last_recorded_time = current_time
                        
                    except ValueError:
                        print(f"無効なデータを受信: {line}")

except serial.SerialException:
    print(f"ポート {SERIAL_PORT} が見つからないか、開けませんでした。")
except KeyboardInterrupt:
    print("\n記録を停止しました。")
finally:
    if "ser" in locals() and ser.is_open:
        ser.close()
        print("シリアルポートを閉じました。")
