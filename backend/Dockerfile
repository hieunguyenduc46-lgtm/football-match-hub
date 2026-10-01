# Used to deploy the backend to any Docker-capable host (Fly.io, Railway...).
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Host must be 0.0.0.0; the port comes from the PORT environment variable (default 8000).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
