import cv2
import time
import threading
import uvicorn
import pygame
import locale
import pandas
import numpy
import shutil

import sekisanondo # unique to this program
from pathlib import Path
from fastapi import FastAPI, Response, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pathlib import Path

app = FastAPI()
latest_frame = None
templates = Jinja2Templates(directory=".")
ALARM_PATH = "alarm.ogg"

#For Image Viewer,
SCRIPT_DIR = Path(__file__).parent.resolve()
PAST_IMAGES_DIR = SCRIPT_DIR / "past_images"
PAST_IMAGES_DIR.mkdir(exist_ok=True)
app.mount("/past_images", StaticFiles(directory=str(PAST_IMAGES_DIR)), name="past_images")

def get_latest_temperature(csv_file_path):
    """Reads the CSV and returns the latest temperature and stats."""
    try:
        df = pandas.read_csv(csv_file_path, parse_dates=["Timestamp"])

        if df.empty:
            print("The CSV file is empty.")
            return {"latest": "N/A", "avg": "N/A", "sum": "N/A", "TET": "N/A"}

        # Calculate metrics
        total_sum = df["Temperature (°C)"].sum()
        average_temp = df["Temperature (°C)"].mean()
        latest_entry = df.iloc[-1]
        TET_Temp = sekisanondo.tempature_sum(csv_file_path)

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

# This route serves the image to your phone
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Fetch live data right when the user requests the page
    script_dir = Path(__file__).parent.resolve()
    csv_path = script_dir / "temperature_log.csv"
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

    # Grab all webp files, sort them newest to oldest
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

        if self.camera_working:
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        else:
            self.create_placeholder_image()
            print("No Camera Detected. It runs on Non-Camera Mode instead. \nDo not use this outside of test purpose.")


    def create_placeholder_image(self):
        """Generates a simple gray image saying 'Camera Not Connected'"""
        # Create a solid gray background (480x640 pixels, 3 color channels)
        placeholder = numpy.zeros((480, 640, 3), dtype=numpy.uint8) + 100

        # Add text to the image
        text = "Camera Not Connected"
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_scale = 1
        text_thickness = 2
        text_color = (255, 255, 255) # White text

        # Figure out text size to center it
        text_size = cv2.getTextSize(text, font, text_scale, text_thickness)[0]
        text_x = (placeholder.shape[1] - text_size[0]) // 2
        text_y = (placeholder.shape[0] + text_size[1]) // 2

        cv2.putText(placeholder, text, (text_x, text_y), font, text_scale, text_color, text_thickness)

        # Save it as the fallback view
        cv2.imwrite("current_view.webp", placeholder, [cv2.IMWRITE_WEBP_QUALITY, 80])

    def run_camera(self):
        if not self.camera_working:
            print("Camera handler is idling smoothly. Server is online.")
            while True:
                time.sleep(1)

        last_save_time = time.time()
        last_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Camera stream disconnected.")
                break

            cv2.imshow("Frame", frame)

            if time.time() - last_save_time >= 10:
                last_save_time = time.time()
                print(last_date_time + ": Image updated on server.")
                last_file_dir = "past_images/" + last_date_time + ".webp"
                shutil.move("current_view.webp", last_file_dir)
                print("The last current_view.webp was moved into: " + last_file_dir)
                cv2.imwrite("current_view.webp", frame, [cv2.IMWRITE_WEBP_QUALITY, 80])
                last_date_time = datetime.now().strftime("%Y%m%d_%H%M%S")

            if cv2.waitKey(1) == 27: break

        self.cap.release()
        cv2.destroyAllWindows()

def start_server():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    handler = VideoHandler()
    threading.Thread(target=start_server, daemon=True).start()
    handler.run_camera()
