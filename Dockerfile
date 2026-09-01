# Use official lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Set working directory
WORKDIR /app

# Upgrade pip and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend source code
COPY backend ./backend
COPY frontend ./frontend
COPY run.py .
COPY .env.example .env

# Expose port (dynamic on cloud hosts like Railway/Render)
EXPOSE 8000

# Start Uvicorn with dynamic $PORT binding for Railway, Render, Heroku & Docker
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
