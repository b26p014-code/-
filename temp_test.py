import time
import board
import adafruit_dht

# Initialize the DHT22 on GPIO 4 (Physical Pin 7)
dhtDevice = adafruit_dht.DHT22(board.D4)

try:
    # Read temperature and humidity
    temperature_c = dhtDevice.temperature
    humidity = dhtDevice.humidity

    print(f"Connection Successful!")
    print(f"Temp: {temperature_c:.1f}°C | Humidity: {humidity:.1f}%")

except RuntimeError as error:
    # Errors are common with DHT sensors due to strict timing requirements.
    # If it keeps failing continuously, the wiring is likely wrong.
    print(f"RuntimeError (Reading failed, but wire might be right): {error.args[0]}")
except Exception as error:
    dhtDevice.exit()
    raise error

dhtDevice.exit()