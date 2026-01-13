FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY splunk_frozen_logs_export/ ./splunk_frozen_logs_export/
COPY main.py .

# Run as CLI script, not web server
ENTRYPOINT ["python3", "main.py"]
