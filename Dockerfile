FROM python:3.11-slim

WORKDIR /app

# Install Node.js, npm, and Docker client
RUN apt-get update && \
    apt-get install -y curl ca-certificates gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    node --version && \
    npm --version && \
    npx --version && \
    docker --version

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY otto/ ./otto/

COPY setup.py .

RUN pip install --no-cache-dir -e .

WORKDIR /config

VOLUME ["/config", "/workspace"]

CMD ["python", "-m", "otto"]
