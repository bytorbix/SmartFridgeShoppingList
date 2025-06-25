FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create necessary directories
RUN mkdir -p uploads ssl_certs static static2/audio data

# Set permissions for SSL certificate generation
RUN chmod 755 ssl_certs

EXPOSE 8000

# Use HTTPS by default, but allow HTTP fallback
CMD ["python", "server.py"]