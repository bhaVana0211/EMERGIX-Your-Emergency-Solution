FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (e.g. for psycopg2, postgis if needed)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Environment variables
ENV FLASK_ENV=production
ENV FLASK_APP=Emergix.app:app

EXPOSE 5000

# Run with eventlet for SocketIO support
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:5000", "Emergix.app:app"]
