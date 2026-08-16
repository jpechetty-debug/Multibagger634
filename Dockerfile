# ── Stage 1: build the web UI (Vite/React) ──────────────────────────────────
FROM node:20-slim AS web-build
WORKDIR /web
COPY web-ui/package.json web-ui/package-lock.json* ./
RUN npm install --ignore-scripts
COPY web-ui/ ./
RUN npm run build

# ── Stage 2: the FastAPI app ─────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Built frontend from stage 1 (web-ui/dist is gitignored — it's built here, not committed)
COPY --from=web-build /web/dist ./web-ui/dist

EXPOSE 9005

CMD ["python", "main.py"]
