FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install uv
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads && \
    chmod +x entrypoint.sh

EXPOSE 3000

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/app/podcasts.db \
    DOWNLOADS_DIR=/app/downloads

ENTRYPOINT ["./entrypoint.sh"]
