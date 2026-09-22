FROM python:3.12-slim

LABEL maintainer="Viora Health Technologies"
LABEL description="Viora – Intelligent Voice Receptionist Backend"

# Security: run as non-root
RUN groupadd -r viora && useradd -r -g viora viora

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source (respect .dockerignore)
COPY --chown=viora:viora . .

# Switch to non-root user
USER viora

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
