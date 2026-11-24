FROM node:24-bookworm-slim AS interface
WORKDIR /frontend
RUN npm install --global pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/tsconfig.json frontend/vite.config.mjs ./
COPY frontend/src/ ./src/
RUN pnpm build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/data
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY database/ ./database/
COPY IA/ ./IA/
COPY frontend/standalone.html ./frontend/standalone.html
COPY --from=interface /frontend/dist/ ./frontend/dist/
RUN mkdir -p /data
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
