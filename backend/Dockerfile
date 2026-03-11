FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Configure git
RUN git config --global user.email "mlvcs@system.local" && \
    git config --global user.name "MLVCS System" && \
    git config --global init.defaultBranch main

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
