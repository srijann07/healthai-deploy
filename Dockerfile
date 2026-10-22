# Multi-stage Dockerfile for HealthAI Cloud Deployment (Hugging Face Spaces, Render, Cloud Run)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    PORT=7860

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

# Set up user 1000 for Hugging Face Spaces compatibility and runtime directories
RUN useradd -m -u 1000 user && \
    mkdir -p uploads ml/artifacts && \
    chown -R user:user /app

USER user

# Expose port (7860 default for Hugging Face Spaces)
EXPOSE 7860

# Production startup with Gunicorn
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-7860} --workers 2 --threads 4 --timeout 120 wsgi:application"]
