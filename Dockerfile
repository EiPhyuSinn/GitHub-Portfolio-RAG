FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements_flask.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Add /app to PYTHONPATH
ENV PYTHONPATH=/app

# Create environment file template
RUN cp .env.example .env

# Expose port for Flask app
EXPOSE 5000

# Default command
CMD ["python", "flask_app.py"]
