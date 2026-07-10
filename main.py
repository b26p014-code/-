import cv2
import time
import threading
import uvicorn
import pygame
import locale
import pandas
import numpy
import shutil
import csv

import sekisanondo # unique to this program
from pathlib import Path
from fastapi import FastAPI, Response, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import board
import adafruit_dht

app = FastAPI()
latest_frame = None
templates = Jinja2Templates(directory=".")
ALARM_PATH = "alarm.ogg"
FILENAME = "temperature_log.csv"

# For Image Viewer
SCRIPT_DIR = Path(__file__).parent.resolve()
PAST_IMAGES_DIR = SCRIPT_DIR / "past_images"
PAST_IMAGES_DIR.mkdir(exist_ok=True)
app.mount("/past_images", StaticFiles(directory=str(PAST_IMAGES_DIR)), name="past_images")

# Ensure the CSV exists and has a header at startup
if not Path(FILENAME).exists():
    with open(FILENAME, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Temperature (°C)"])

def get_latest_temperature(csv_file_path):
    """Reads the CSV and returns the latest temperature and stats."""
    try:
        df = pandas.read_csv(csv_file_path, parse_dates=["Timestamp"])

        if df.empty:
            print("The CSV file is empty.")
            return {"latest": "N/A", "avg": "N/A", "sum": "N/A", "TET": "N/A"}
        
        date_file = ("sekisan_tmp.txt")
        with open(date_file, mode='r', encoding="utf-8") as f:
            sekisan_date = f.read().strip()
            print(f"Loaded date from file: {sekisan_date}")

        #total_sum = df["Temperature (°C)"].sum()
        average_temp = df["Temperature (°C)"].mean()
        latest_entry = df.iloc[-1]
        TET_Temp, total_sum = sekisanondo.tempature_sum(csv_file_path, sekisan_date)

        print(f"--- Live Update: Latest Temp is {latest_entry['Temperature (°C)']}°C ---")

        return {
            "latest": f"{latest_entry['Temperature (°C)']:.1f}",
            "avg": f"{average_temp:.1f}",
            "sum": f"{total_sum:.1f}",
            "TET": f"{TET_Temp:.1f}"
        }

    except FileNotFoundError:
        print(f"Error: The file at '{csv_file_path}' was not found.")
        return {"latest": "N/A", "avg": "N/A", "sum": "N/A", "TET": "N/A"}
    except KeyError:
        print("Error: Column name mismatch in CSV.")
        return {"latest": "N/A", "avg": "N/A", "sum": "N/A", "TET": "N/A"}


@app.post("/trigger-alarm")
@app.get("/trigger-alarm")
async def trigger_alarm():
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(ALARM_PATH)
        pygame.mixer.music.play()
        print("Alarm Triggered!")
        return {"status": "success", "message": "Alarm is playing"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/send-date")
@app.get("/send-date")
async def send_date(date: str = None):
    try:
        if date:
            print(f"Received date from website: {date}")
            # You can now parse it into a datetime object if needed:
            date_obj = datetime.strptime(date, "%Y-%m-%d")

            s = {date}
            save_path = Path("sekisan_tmp.txt")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, mode='w', encoding="utf-8") as f:
                f.write(date)

            with open(save_path, mode='r', encoding="utf-8") as f:
                print(f.read())

            f.close()
            return {"status": "success", "message": f"Date {date} received successfully"}
        else:
            print("Send-date endpoint hit, but no date was provided.")
            return {"status": "error", "message": "No date provided"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    script_dir = Path(__file__).parent.resolve()
    csv_path = script_dir / FILENAME
    stats = get_latest_temperature(csv_path)

    return templates.TemplateResponse(
        request=request,
        name="website.html",
        context={
            "tempature_to_show": stats["latest"],
            "avg_temp": stats["avg"],
            "sum_temp": stats["sum"],
            "TET": stats["TET"]
        }
    )

@app.get("/latest")
async def get_latest():
    return FileResponse("current_view.webp", media_type="image/webp")

@app.get("/history", response_class=HTMLResponse)
async def history_viewer(request: Request):
    history_dir = Path("past_images")
    if history_dir.exists():
        images = [f.name for f in history_dir.glob("*.webp")]
        images.sort(reverse=True)
    else:
        images = []

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={"images": images}
    )

class VideoHandler:
    def __init__(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self.camera_working = self.cap.isOpened()

        # Initialize DHT22 (Change D18 to your actual GPIO if needed, e.g., D4)
        self.dhtDevice = adafruit_dht.DHT22(board.D18)

        if self.camera_working:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        else:
            self.create_placeholder_image()
            print("No Camera Detected. Running in Non-Camera Mode.")

    def create_placeholder_image(self):
        placeholder = numpy.zeros((480, 640, 3), dtype=numpy.uint8) + 100
        text = "Camera Not Connected"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_size = cv2.getTextSize(text, font, 1, 2)[0]
        text_x = (placeholder.shape[1] - text_size[0]) // 2
        text_y = (placeholder.shape[0] + text_size[1]) // 2
        cv2.putText(placeholder, text, (text_x, text_y), font, 1, (255, 255, 255), 2)
        cv2.imwrite("current_view.webp", placeholder, [cv2.IMWRITE_WEBP_QUALITY, 80])

    def record_temperature(self, now_str):
        """Helper to read DHT22 and write to CSV."""
        try:
            temperature = self.dhtDevice.temperature
            if temperature is not None:
                with open(FILENAME, mode="a", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    writer.writerow([now_str, temperature])
                print(f"[{now_str}] Temp Logged: {temperature} °C")
                return temperature
        except RuntimeError as error:
            # DHT sensors fail often, log the error but do not crash
            print(f"DHT Read Error: {error.args[0]}")
        return None

    def run_camera(self):
        last_save_time = time.time()
        last_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Fallback simulation loop if camera doesn't work but we still want synced sensor logs
        if not self.camera_working:
            print("Camera handler is idling smoothly. Server is online.")
            while True:
                if time.time() - last_save_time >= 1800: #30 minutes
                    last_save_time = time.time()
                    now_formatted = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.record_temperature(now_formatted)
                time.sleep(1)

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Camera stream disconnected.")
                break

            cv2.imshow("Frame", frame)

            # --- SYNCHRONIZED SNAPSHOT AND SENSOR EVENT ---
            if time.time() - last_save_time >= 10:
                last_save_time = time.time()
                
                # 1. Grab consistent timestamp for both actions
                now_raw = datetime.now()
                now_file_str = now_raw.strftime("%Y%m%d_%H%M%S")
                now_csv_str = now_raw.strftime("%Y-%m-%d %H:%M:%S")

                # 2. Take Temperature 
                self.record_temperature(now_csv_str)

                # 3. Take Picture (Move old current view, write new frame)
                print(f"{now_file_str}: Image updated on server.")
                last_file_dir = f"past_images/{last_date_time}.webp"
                
                if Path("current_view.webp").exists():
                    shutil.move("current_view.webp", last_file_dir)
                    print("The last current_view.webp was moved into: " + last_file_dir)
                
                cv2.imwrite("current_view.webp", frame, [cv2.IMWRITE_WEBP_QUALITY, 80])
                
                # Update tracker with current timestamp name for next cycle
                last_date_time = now_file_str

            if cv2.waitKey(1) == 27: 
                break

        self.cap.release()
        cv2.destroyAllWindows()
        self.dhtDevice.exit()

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    handler = VideoHandler()
    threading.Thread(target=start_server, daemon=True).start()
    handler.run_camera()
