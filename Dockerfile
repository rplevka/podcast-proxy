FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p downloads && \
    chmod +x entrypoint.sh

EXPOSE 3000

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/app/podcasts.db \
    DOWNLOADS_DIR=/app/downloads

ENTRYPOINT ["./entrypoint.sh"]
