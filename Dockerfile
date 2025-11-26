FROM python:3.11-slim

WORKDIR /app

# Install Node.js and npm
RUN apt-get update && \
    apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    node --version && \
    npm --version && \
    npx --version

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY otto/ ./otto/

COPY setup.py .

RUN pip install --no-cache-dir -e .

WORKDIR /config

VOLUME ["/config", "/workspace"]

CMD ["python", "-m", "otto"]
