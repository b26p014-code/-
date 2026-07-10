import csv
from datetime import datetime

# 保存するCSVファイル名
FILENAME = "temperature_date_log.csv"

def tempature_sum(file_path, sekisan_date):

    #ファイル名(どちらかコメントアウトして使う)
    #file_path = "temperature_log.csv" #シュミレーション用ファイル
    #file_path = "sensor_data.csv"     #実機用ファイル
    temps = [] #日平均気温を格納


    # --- 1. 標準入力から計算開始日を受け取る (Web上から入力できるようにしたい...)---
    print("トマトの花が受粉した日(ホルモン処理した日)を入力してください")
    print("入力例: 2026-06-19")
    #user_input = input("開始日 > ")
    

    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        timestamps = [row['Timestamp'] for row in reader]
        oldest_timestamp = min(timestamps)
        oldest_day = oldest_timestamp.split(' ')[0]

    try:
        # 入力された文字列を日付データ（時間の初期値は 00:00:00）に変換
        day = datetime.strptime(sekisan_date, "%Y-%m-%d")
    except ValueError:
        print("【エラー】入力形式が正しくありません。'2026-06-19' のように入力してください。")
        return -1.0  # エラーのため、プログラムを強制終了させるのではなく、-1を出力

    # 日付ごとのデータを記録するための辞書
    # 構造例: {"2026-06-19": {"total_temp": 508.8, "count": 23}}
    daily_data = {}


    # ---2. CSVファイルを読み込んで日別に集計---
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            # 文字列を一度日時のオブジェクトに変換
            row_datetime = datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")

            # 基準日以降のデータのみ対象にする
            if row_datetime >= day:
                # 日時オブジェクトから「年-月-日」の文字列だけを抽出 (例: "2026-06-19")
                date_str = row_datetime.strftime("%Y-%m-%d")
                temp_value = float(row["Temperature (°C)"])

                # まだ辞書にその日の一覧がなければ初期化
                if date_str not in daily_data:
                    daily_data[date_str] = {"total_temp": 0.0, "count": 0}

                # その日の「合計温度」と「データ数」を足していく
                daily_data[date_str]["total_temp"] += temp_value
                daily_data[date_str]["count"] += 1


    # ---3. 結果の出力---
    print("\n" + "="*45)
    print(f" {oldest_day} 以降の1日ごとの集計結果 (標準csv)")
    print("="*45)

    if daily_data:
        # 日付の古い順に並び替えて出力
        for date_str in sorted(daily_data.keys()):
            total = daily_data[date_str]["total_temp"]
            count = daily_data[date_str]["count"]
            # 平均を計算
            avg_temp = total / count

            print(f"日付: {date_str} | データ数: {count}件 | 平均温度: {avg_temp:.1f}°C")
            temps.append(avg_temp) #1日の平均温度を行列に格納

            # CSVファイルに格納（mode='a'）
            with open(FILENAME, mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([avg_temp])
    else:
        print(" 該当するデータがありませんでした。")

    print("="*45)

    # ---4. 積算温度の出力---
    sekisanondo = 0.0

    for temp in temps:
        sekisanondo = sekisanondo + temp

    print(f"積算温度={sekisanondo:.1f}℃")

    if temps and temps[-1] > 0:
        last_temp = temps[-1]
        date_count=(1200 - sekisanondo)/ temp
        print(f"収穫までの日数(予想)：{date_count:.1f}日")
    else:
        print("The math is not functional, We puke date_count as a 0.")
        date_count = 0.0

    return sekisanondo, date_count
