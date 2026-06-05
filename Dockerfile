FROM python:3.12-slim

WORKDIR /app

# Set environment variables to prevent python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install required system packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create a non-root user
RUN useradd -m botuser && \
    mkdir -p /app/data && \
    chown -R botuser:botuser /app
USER botuser

# Command to run the bot
CMD ["python", "main.py"]
