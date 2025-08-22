# Multi-stage Dockerfile for production-ready GRC Platform

# Build stage
FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.12-slim as production

# Build arguments
ARG BUILD_ENV=production
ARG BUILD_DATE
ARG BUILD_VERSION
ARG BUILD_COMMIT

# Labels for container metadata
LABEL org.opencontainers.image.title="GRC Platform"
LABEL org.opencontainers.image.description="Multi-tenant GRC SaaS Platform"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.version="${BUILD_VERSION}"
LABEL org.opencontainers.image.revision="${BUILD_COMMIT}"
LABEL org.opencontainers.image.vendor="Your Company"
LABEL maintainer="your-team@company.com"

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=app.settings.production \
    PATH="/opt/venv/bin:$PATH" \
    BUILD_ENV=${BUILD_ENV} \
    APP_VERSION=${BUILD_VERSION} \
    BUILD_COMMIT=${BUILD_COMMIT}

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create workspace and set permissions
WORKDIR /workspace
RUN mkdir -p /workspace/app /workspace/static /workspace/media && \
    chown -R appuser:appuser /workspace

# Copy application code
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser scripts ./scripts

# Make scripts executable
RUN chmod +x ./scripts/startup.sh

# Create log directory
RUN mkdir -p /home/LogFiles && chown appuser:appuser /home/LogFiles

# Switch to non-root user
USER appuser

# Working directory for Django
WORKDIR /workspace/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/ || exit 1

# Expose port
EXPOSE 8000

# Default command - use startup script
CMD ["/workspace/scripts/startup.sh"]