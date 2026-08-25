# Multi-stage Dockerfile for HealthAI Cloud Deployment
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=8080

WORKDIR /app

# Install system dependencies needed for compilation / postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure upload and ML directories exist
RUN mkdir -p uploads ml/artifacts

# Expose port (Cloud Run defaults to 8080, Render maps dynamic PORT)
EXPOSE 8080

# Production startup with Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 wsgi:application"]
