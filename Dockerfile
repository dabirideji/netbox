FROM node:22-alpine AS frontend

WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NETBOX_ENV=production

RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app
COPY backend ./backend
COPY config ./config
COPY .env.production README.md ./
COPY --from=frontend /app/frontend/dist ./frontend/dist

RUN python -m pip install --no-cache-dir ./backend

USER appuser
EXPOSE 4177

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4177/api/status', timeout=3).read()"

ENTRYPOINT ["netbox"]
CMD ["--host", "0.0.0.0", "--port", "4177"]
