# syntax=docker/dockerfile:1

# --- Build the web app ---
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- API server that also serves the built web app ---
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FITAI_ENVIRONMENT=production \
    FITAI_STATIC_DIR=/app/web/dist \
    PORT=8000

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=web /web/dist /app/web/dist

RUN useradd --create-home --uid 1000 fitai && chown fitai /app/backend
USER fitai

EXPOSE 8000
# Migrations run automatically on startup. Hosting platforms set $PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
