# SDS011 to MQTT Forwarder

A lightweight Docker container that reads air quality data from an SDS011 particulate matter sensor and forwards it to an MQTT broker. Designed for integration with ThingsBoard IoT platform but works with any MQTT broker.

## Features

- **Real-time Air Quality Monitoring**: Reads PM2.5 and PM10 measurements from SDS011 sensor
- **AQI Calculation**: Automatically calculates Air Quality Index based on EPA standards
- **Multiple Authentication Modes**: Supports device token, gateway credentials, or anonymous connection
- **Docker Ready**: Runs as a containerized service with USB device passthrough
- **Multi-Architecture**: Supports amd64, arm64, and arm/v7 platforms
- **Automatic Reconnection**: Handles MQTT and sensor connection failures gracefully
- **Health Monitoring**: Built-in healthcheck for container orchestration

## Prerequisites

- Docker and Docker Compose
- SDS011 sensor connected via USB (typically appears as `/dev/ttyUSB0`)
- MQTT broker (e.g., ThingsBoard Gateway MQTT Connector)

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sds011_to_mqtt_forwarder
   ```

2. **Configure environment**
   ```bash
   cp .env.default .env
   # Edit .env with your settings
   ```

3. **Run with Docker Compose**
   ```bash
   docker compose up -d
   ```

4. **Check logs**
   ```bash
   docker compose logs -f sds011
   ```

## Configuration

Create a `.env` file with the following variables:

### Sensor Configuration
```bash
SERIAL_PORT=/dev/ttyUSB0                    # USB serial port
DEVICE_NAME=DustAirSensor1                  # Device identifier
DEVICE_PROFILE=AirQualitySensor_SDS011      # ThingsBoard device profile
```

### MQTT Broker
```bash
GATEWAY_HOST=mqtt-broker                    # MQTT broker hostname
GATEWAY_PORT=1883                           # MQTT broker port
```

### Authentication Mode

Choose one of three authentication modes:

#### Option 1: Anonymous (simplest)
```bash
AUTH_MODE=anonymous
```

#### Option 2: Gateway Authentication
```bash
AUTH_MODE=gateway
MQTT_USERNAME=your_username
MQTT_PASSWORD=your_password
MQTT_CLIENT_ID=sds011-sensor-01            # Optional
```

#### Option 3: Device Token (ThingsBoard)
```bash
AUTH_MODE=device
TB_ACCESS_TOKEN=your_device_token
```

### Logging
```bash
LOG_LEVEL=INFO                              # DEBUG, INFO, WARNING, ERROR
```

## Data Format

The sensor publishes JSON telemetry to the MQTT broker:

```json
{
  "deviceName": "DustAirSensor1",
  "deviceProfile": "AirQualitySensor_SDS011",
  "timestamp": 1702123456789,
  "pm25": 12.5,
  "pm10": 18.3,
  "aqi": 52.0,
  "aqi_pm25": 52.0,
  "aqi_pm10": 17.0
}
```

### MQTT Topics

- **Device mode**: `v1/devices/me/telemetry`
- **Gateway/Anonymous mode**: `v1/gateway/telemetry`

## Docker Deployment

### Using Docker Compose (Recommended)

The `compose.yml` file includes:
- USB device passthrough
- Persistent logging volume
- Healthcheck monitoring
- External network connection

```bash
# Start service
docker compose up -d

# Stop service
docker compose down

# View logs
docker compose logs -f sds011

# Restart service
docker compose restart sds011
```

### Using Docker Run

```bash
docker run -d \
  --name sds011-forwarder \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  --privileged \
  --env-file .env \
  -v sds011-logs:/app/logs \
  registry.nimahosts.com/hubo/sds011-to-mqtt-forwarder:latest
```

## Building from Source

```bash
# Build image
docker build -t sds011-forwarder .

# Run locally
docker run -d \
  --name sds011-forwarder \
  --device /dev/ttyUSB0:/dev/ttyUSB0 \
  --privileged \
  --env-file .env \
  sds011-forwarder
```

## Troubleshooting

### Sensor not detected
- Verify USB connection: `ls -l /dev/ttyUSB*`
- Check container has device access: `docker compose ps`
- Ensure `privileged: true` is set in compose.yml

### MQTT connection failures
- Verify broker hostname is reachable from container
- Check network configuration in compose.yml
- Verify authentication credentials
- Review logs: `docker compose logs sds011`

### No data being published
- Check healthcheck status: `docker compose ps`
- Verify sensor readings: Look for "Telemetry sent" in logs
- Ensure sensor is not being used by another process

### Permission denied on serial port
- Add user to dialout group: `sudo usermod -a -G dialout $USER`
- Ensure container runs as privileged
- Restart Docker daemon after group changes

## Health Monitoring

The container includes a healthcheck that verifies telemetry is being sent:
- **Interval**: 20 seconds
- **Timeout**: 5 seconds
- **Retries**: 5 attempts
- **Start period**: 15 seconds (initial grace period)

Check health status:
```bash
docker compose ps
# or
docker inspect sds011-forwarder --format='{{.State.Health.Status}}'
```

## Logs

Logs are stored in a Docker volume and include:
- Connection events
- Telemetry readings
- Error messages
- Rotation: 1MB max size, 5 backup files

Access logs:
```bash
# Via Docker Compose
docker compose logs -f sds011

# Direct log file access
docker exec sds011-forwarder cat /app/logs/sds011.log
```

## Integration with ThingsBoard

1. Create a device in ThingsBoard with profile `AirQualitySensor_SDS011`
2. Configure ThingsBoard Gateway MQTT Connector
3. Set up the external network:
   ```bash
   docker network create tbgw
   ```
4. Configure `.env` with appropriate authentication mode
5. Start the forwarder - it will connect to the gateway network

## Hardware Requirements

- **SDS011 Laser PM2.5 Sensor**: Nova Fitness SDS011 particulate matter sensor
- **USB-to-Serial Adapter**: Usually included with SDS011
- **Host System**: Any system supporting Docker with USB port (Raspberry Pi, x86_64, etc.)

## License

[Add your license information here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Maintainer: Martin Kovachev <miracle@nimasystems.com>
