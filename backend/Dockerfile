# -------------------------------
# Stage 1 — Build dependencies
# -------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install minimal build dependencies for psycopg2, cryptography, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev libffi-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies into an isolated prefix
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --prefix=/install --no-cache-dir -r requirements.txt \
 && find /install -type d -name "__pycache__" -exec rm -rf {} + \
 && find /install -type f -name "*.pyc" -delete


# -------------------------------
# Stage 2 — Runtime image
# -------------------------------
FROM python:3.11-slim

WORKDIR /app

# Install only runtime tools (Graphviz, fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz fonts-dejavu libmagic1 tzdata \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies (from builder only)
COPY --from=builder /install /usr/local

# Copy source code
COPY . .

# Environment optimizations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Optional security: run as non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
