#!/bin/bash
set -e

echo "Starting Podcast RSS Proxy..."

if [ ! -f "$DB_PATH" ]; then
    echo "Database not found at $DB_PATH, it will be created automatically..."
fi

if [ ! -d "$DOWNLOADS_DIR" ]; then
    echo "Creating downloads directory at $DOWNLOADS_DIR..."
    mkdir -p "$DOWNLOADS_DIR"
fi

echo "Initializing database and starting application..."
exec python app.py
