FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home app
COPY backend/ ./
COPY --from=frontend /build/dist ./static
RUN chmod +x /app/entrypoint.sh
USER app
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
