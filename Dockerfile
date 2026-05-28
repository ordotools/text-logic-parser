# Use the official lightweight Python 3.12 slim image.
FROM python:3.12-slim

# Allow statements and log messages to immediately appear in the logs.
ENV PYTHONUNBUFFERED=True

# Create and set the working directory.
WORKDIR /app

# Copy local code to the container image.
COPY . /app

# Install production dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup.
# Cloud Run automatically sets the PORT environment variable.
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
