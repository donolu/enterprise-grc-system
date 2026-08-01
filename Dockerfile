# Multi-stage Dockerfile for production-ready GRC Platform

# Build stage
# Keep the OS release explicit. The unqualified slim tag moved from Bookworm
# to Trixie, changing the vulnerability and native-library surface underneath
# otherwise identical application builds.
FROM python:3.13-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libmagic1 \
    libxml2-dev \
    libxmlsec1-dev \
    libxslt1-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /build
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --no-binary=lxml,xmlsec -r requirements.txt

# Production stage
FROM python:3.13-slim-bookworm AS production

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
    HOME="/home/appuser" \
    XDG_CACHE_HOME="/home/appuser/.cache" \
    PATH="/opt/venv/bin:$PATH" \
    BUILD_ENV=${BUILD_ENV} \
    APP_VERSION=${BUILD_VERSION} \
    BUILD_COMMIT=${BUILD_COMMIT}

# Install runtime dependencies
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libexpat1 \
    libmagic1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libxml2 \
    libxmlsec1 \
    libxmlsec1-openssl \
    libxslt1.1 \
    && apt-get purge -y --allow-remove-essential apt perl-base \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /var/log/apt/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Runtime containers do not need package-management tooling.
RUN /opt/venv/bin/python -m pip uninstall -y pip wheel virtualenv && \
    /usr/local/bin/python -m pip uninstall -y pip wheel

# Create workspace and set permissions
WORKDIR /workspace
RUN mkdir -p /workspace/app /workspace/static /workspace/media && \
    chown -R appuser:appuser /workspace

# Copy application code
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser scripts ./scripts

# Make scripts executable
RUN chmod +x ./scripts/startup.sh

# Create writable runtime directories for logs and font caches
RUN mkdir -p /home/LogFiles /home/appuser/.cache/fontconfig && \
    chown -R appuser:appuser /home/LogFiles /home/appuser

# Switch to non-root user
USER appuser

# Working directory for Django
WORKDIR /workspace/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://localhost:%s/health/' % os.environ.get('PORT', '8000'), timeout=10).read()"]

# Expose port
EXPOSE 8000

# Default command - use startup script
CMD ["/workspace/scripts/startup.sh"]
