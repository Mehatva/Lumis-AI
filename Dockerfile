# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=backend/app.py
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install ONLY the bare essentials to stay light
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend and frontend folders
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create instance folder for SQLite
RUN mkdir -p /app/backend/instance

# Expose the port the app runs on
EXPOSE 5001

# Command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "120", "backend.app:create_app()"]
