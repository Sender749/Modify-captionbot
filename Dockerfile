# Base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy repo
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    build-essential \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create logs directory
RUN mkdir -p /app/logs

# Expose Flask port
EXPOSE 5000

# Start supervisord
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
