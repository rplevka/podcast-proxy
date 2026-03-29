#!/bin/bash
set -e

echo "Starting Podcast RSS Proxy..."

if [ ! -d "$DOWNLOADS_DIR" ]; then
    echo "Creating downloads directory at $DOWNLOADS_DIR..."
    mkdir -p "$DOWNLOADS_DIR"
fi

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Database not found. Creating initial database schema..."
    python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database created successfully')"
    
    echo "Stamping database with current migration version..."
    flask db stamp head
else
    echo "Database exists. Running migrations..."
    flask db upgrade
fi

echo "Starting application..."
exec python app.py
