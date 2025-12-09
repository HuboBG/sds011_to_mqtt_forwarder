import os
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import aqi
import paho.mqtt.client as mqtt
from sds011lib import SDS011QueryReader


# ========================
# CONFIG
# ========================

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
DEVICE_NAME = os.getenv("DEVICE_NAME", "DustSensor01")
DEVICE_PROFILE = os.getenv("DEVICE_PROFILE", "AirQualitySensor_SDS011")

GATEWAY_HOST = os.getenv("GATEWAY_HOST", "mqtt-broker")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "1883"))

AUTH_MODE = os.getenv("AUTH_MODE", "gateway").lower()   # gateway | device | anonymous

TB_ACCESS_TOKEN = os.getenv("TB_ACCESS_TOKEN")          # for AUTH_MODE=device
MQTT_USERNAME = os.getenv("MQTT_USERNAME")              # for AUTH_MODE=gateway
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


# ========================
# LOGGING
# ========================

LOG_DIR = "/app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("sds011")
logger.setLevel(LOG_LEVEL)

fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")

console = logging.StreamHandler()
console.setFormatter(fmt)
logger.addHandler(console)

filelog = RotatingFileHandler(f"{LOG_DIR}/sds011.log", maxBytes=1_000_000, backupCount=5)
filelog.setFormatter(fmt)
logger.addHandler(filelog)

logger.info("Starting SDS011 Air Quality Forwarder (sds011lib version)")
logger.info(f"Serial port: {SERIAL_PORT}")
logger.info(f"Auth mode: {AUTH_MODE}")


# ========================
# MQTT CLIENT
# ========================

mqtt_client = mqtt.Client(
    client_id=MQTT_CLIENT_ID,
    protocol=mqtt.MQTTv5,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

if AUTH_MODE == "device":
    if not TB_ACCESS_TOKEN:
        logger.error("AUTH_MODE=device requires TB_ACCESS_TOKEN.")
        raise SystemExit(1)
    mqtt_client.username_pw_set(TB_ACCESS_TOKEN)
    logger.info("Using device token authentication")

elif AUTH_MODE == "gateway":
    if MQTT_USERNAME:
        mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        logger.info(f"Using gateway MQTT authentication (username={MQTT_USERNAME})")
    else:
        logger.warning("AUTH_MODE=gateway WITHOUT MQTT_USERNAME — connecting anonymously.")

elif AUTH_MODE == "anonymous":
    logger.info("Using anonymous MQTT connection")
else:
    logger.error(f"Unknown AUTH_MODE={AUTH_MODE}")
    raise SystemExit(1)


# connect with retry
while True:
    try:
        mqtt_client.connect(GATEWAY_HOST, GATEWAY_PORT, keepalive=60)
        logger.info("Connected to MQTT broker")
        break
    except Exception as e:
        logger.error(f"MQTT connect failed: {e}")
        time.sleep(5)


# MQTT Topic
if AUTH_MODE == "device":
    topic = "v1/devices/me/telemetry"
else:
    topic = "v1/gateway/telemetry"

logger.info(f"Using telemetry topic: {topic}")


# ========================
# SDS011 SENSOR (sds011lib)
# ========================

try:
    reader = SDS011QueryReader(SERIAL_PORT)
    logger.info("SDS011QueryReader initialized successfully")
except Exception as e:
    logger.error(f"Failed to open SDS011 sensor: {e}")
    raise SystemExit(1)


# ========================
# MAIN LOOP
# ========================

while True:
    try:
        # read 1 measurement
        datum = reader.query()     # this already handles wake/query mode

        if not datum:
            logger.warning("No data returned from SDS011 sensor")
            time.sleep(5)
            continue

        pm25 = float(datum.pm25)
        pm10 = float(datum.pm10)

        # compute AQI
        myaqi = aqi.to_aqi([
            (aqi.POLLUTANT_PM25, str(pm25)),
            (aqi.POLLUTANT_PM10, str(pm10)),
        ])
        aqiv = float(myaqi)

        payload = {
            "deviceName": DEVICE_NAME,
            "deviceProfile": DEVICE_PROFILE,
            "timestamp": int(time.time() * 1000),
            "pm25": pm25,
            "pm10": pm10,
            "aqi": aqiv,
            "aqi_pm25": float(aqi.to_aqi([(aqi.POLLUTANT_PM25, str(pm25))])),
            "aqi_pm10": float(aqi.to_aqi([(aqi.POLLUTANT_PM10, str(pm10))])),
        }

        mqtt_client.publish(topic, json.dumps(payload))
        logger.info(f"Telemetry sent: {payload}")

        time.sleep(2)

    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        time.sleep(5)
