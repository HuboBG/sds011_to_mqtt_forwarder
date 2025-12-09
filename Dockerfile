FROM python:3.11-slim

LABEL maintainer="Martin Kovachev <miracle@nimasystems.com>"

# Set working directory
WORKDIR /app

# Install system dependencies for serial ports
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY app/requirements.txt .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/sds011_to_tb.py .

# Create logs directory
RUN mkdir -p /app/logs

# Default environment variables
ENV SERIAL_PORT=/dev/ttyUSB0 \
    LOG_LEVEL=INFO \
    AUTH_MODE=gateway

# Expose nothing (MQTT client only)
CMD ["python3", "sds011_to_tb.py"]
