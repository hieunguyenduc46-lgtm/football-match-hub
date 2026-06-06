# Dùng để deploy backend lên bất kỳ host nào hỗ trợ Docker (Fly.io, Railway...).
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Host phải là 0.0.0.0; cổng lấy từ biến môi trường PORT (mặc định 8000).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
