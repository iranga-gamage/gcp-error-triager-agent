# Use Python 3.13 slim image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install uv for fast package management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .python-version ./

# Install dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV GCP_PROJECT_ID=""

# Expose port
EXPOSE 8080

# Run the application using gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 --chdir src main:app
