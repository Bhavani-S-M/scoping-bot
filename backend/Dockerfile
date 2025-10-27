# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies into a temporary folder
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt

 
# Stage 2: Runtime image
FROM python:3.11-slim
WORKDIR /app

# Install Graphviz system binary (needed for architecture diagrams)
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz fonts-dejavu \
 && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
