# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an IoT data forwarder that reads air quality measurements from an SDS011 particulate matter sensor over USB serial and publishes them to an MQTT broker (specifically designed for ThingsBoard Gateway integration). The application runs as a containerized service with USB device passthrough.

## Architecture

### Single-File Application
- `app/sds011_to_tb.py` - Main application containing all logic:
  - Serial port communication with SDS011 sensor using `sds011lib`
  - MQTT client connection and publishing using `paho-mqtt`
  - AQI (Air Quality Index) calculation using `python-aqi` library
  - Rotating file logging to `/app/logs/sds011.log`
  - Continuous polling loop (2 second intervals between readings)

### Authentication Modes
The application supports three MQTT authentication modes (via `AUTH_MODE` env var):
- `device` - Uses ThingsBoard device access token (`TB_ACCESS_TOKEN`), publishes to `v1/devices/me/telemetry`
- `gateway` - Uses MQTT username/password (`MQTT_USERNAME`, `MQTT_PASSWORD`), publishes to `v1/gateway/telemetry`
- `anonymous` - No authentication, publishes to `v1/gateway/telemetry`

### Payload Structure
Published JSON includes:
- `deviceName`, `deviceProfile` - Device identification
- `timestamp` - Unix milliseconds
- `pm25`, `pm10` - Raw particulate matter readings (µg/m³)
- `aqi` - Combined AQI from both PM2.5 and PM10
- `aqi_pm25`, `aqi_pm10` - Individual AQI values

### Container Architecture
- **USB Passthrough**: Requires `devices: ["/dev/ttyUSB0:/dev/ttyUSB0"]` and `privileged: true` in compose.yml
- **External Network**: Connects to `tbgw` network (ThingsBoard Gateway MQTT broker location)
- **Healthcheck**: Monitors log file for "Telemetry sent" message every 20s
- **Logging Volume**: Persists logs to named volume for debugging

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -r app/requirements.txt

# Run locally (requires USB sensor access)
SERIAL_PORT=/dev/ttyUSB0 python3 app/sds011_to_tb.py

# Configure via environment variables (see .env.default)
```

### Docker Development
```bash
# Build image locally
docker build -t sds011-forwarder .

# Run with compose (requires .env file configured)
docker compose up -d

# View logs
docker compose logs -f sds011

# Check healthcheck status
docker compose ps

# Stop service
docker compose down
```

### CI/CD
- GitHub Actions workflow: `.github/workflows/docker-publish.yml`
- Builds multi-architecture images (amd64, arm64, arm/v7) on tag push
- Pushes to custom registry: `registry.nimahosts.com/hubo/sds011-to-mqtt-forwarder`
- Tags: `latest`, commit SHA, and git tag version
- Sends Slack notifications on success/failure

## Configuration

All configuration is via environment variables. Copy `.env.default` to `.env` and configure:

**Required**:
- `SERIAL_PORT` - USB serial device path (default: `/dev/ttyUSB0`)
- `GATEWAY_HOST` - MQTT broker hostname
- `GATEWAY_PORT` - MQTT broker port (default: `1883`)
- `AUTH_MODE` - Authentication mode: `device`, `gateway`, or `anonymous`

**Auth-dependent**:
- For `device` mode: `TB_ACCESS_TOKEN`
- For `gateway` mode: `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_CLIENT_ID`

**Optional**:
- `DEVICE_NAME` - Device identifier (default: `DustSensor01`)
- `DEVICE_PROFILE` - ThingsBoard device profile (default: `AirQualitySensor_SDS011`)
- `LOG_LEVEL` - Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR`

## Key Implementation Details

### Error Handling
- MQTT connection retries indefinitely with 5-second backoff (app/sds011_to_tb.py:91-98)
- Main loop catches exceptions and continues after 5-second delay (app/sds011_to_tb.py:162-164)
- System exits on critical failures: missing auth credentials or sensor initialization failure

### SDS011 Sensor Communication
- Uses `SDS011QueryReader.query()` which handles wake/sleep cycles automatically
- Sensor wakes, performs measurement, returns reading, then sleeps (no manual sleep management needed)

### Logging Strategy
- Dual output: console (stdout) and rotating file log (1MB max, 5 backups)
- Log file location: `/app/logs/sds011.log`
- Healthcheck depends on "Telemetry sent" message appearing in log file

## Dependencies

Python packages (app/requirements.txt):
- `paho-mqtt>=1.6` - MQTT v5 client
- `pyserial` - USB serial communication
- `sds011lib` - SDS011 sensor library (handles query mode)
- `python-aqi` - AQI calculation from EPA standards
