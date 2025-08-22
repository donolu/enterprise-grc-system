FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libffi-dev libpango-1.0-0 libpangoft2-1.0-0 \
    libcairo2 libpq-dev libmagic1 libreoffice-java-common libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
WORKDIR /workspace/app

ENV DJANGO_SETTINGS_MODULE=app.settings.local
EXPOSE 8000