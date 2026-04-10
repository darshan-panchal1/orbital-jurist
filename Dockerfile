FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (gcc needed for sgp4/numpy wheels)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install project dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod

# Copy application code
COPY . .

# Create required runtime directories
RUN mkdir -p data results logs

# Ensure Python packages are discoverable
RUN touch agents/__init__.py \
         mcp_servers/__init__.py \
         workflow/__init__.py \
         utils/__init__.py \
         prompts/__init__.py

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# RunPod serverless entrypoint
CMD ["python3", "-u", "rp_handler.py"]