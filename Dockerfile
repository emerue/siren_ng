# ── Stage 1: Build the React frontend ──
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python app ──
FROM python:3.13-slim

WORKDIR /app

# Install Python dependencies
# psycopg[binary] bundles its own libpq — no system libpq-dev needed
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create staticfiles dir so WhiteNoise doesn't error before collectstatic runs
RUN mkdir -p staticfiles

# Make startup script executable
RUN chmod +x /app/start.sh

EXPOSE 8080

CMD ["/app/start.sh"]
