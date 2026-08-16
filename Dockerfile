FROM python:3.11-slim

# Install system dependencies including the Docker CLI binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://get.docker.com | sh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn requests pydantic httpx docker

# Copy local script files
COPY server.py index.html /app/

EXPOSE 7860

CMD ["python", "server.py"]