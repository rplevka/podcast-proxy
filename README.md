# Podcast RSS Proxy

A Python-based web server that acts as a podcast RSS proxy. It allows you to add multiple podcast RSS feeds, automatically syncs episodes, downloads them on-demand (acting as a cache), and regenerates new RSS feeds pointing to the cached files.

## Features

- **Feed Management**: Add and manage multiple podcast RSS feeds
- **Automatic Syncing**: Background sync every hour to fetch new episodes
- **On-Demand Caching**: Episodes are downloaded automatically when accessed
- **RSS Regeneration**: Generates new RSS feeds pointing to cached episodes
- **Modern Web UI**: Beautiful interface to manage feeds and episodes
- **RESTful API**: Full API for programmatic access

## Installation

### Option 1: Docker (Recommended)

1. **Using Docker Compose**:
   ```bash
   ./docker-compose up -d
   ```

2. **Or build and run manually**:
   ```bash
   docker build -t podcast-rss-proxy .
   docker run -d -p 3000:3000 \
     -e DB_PATH=/app/data/podcasts.db \
     -v $(pwd)/downloads:/app/downloads \
     -v $(pwd)/data:/app/data \
     podcast-rss-proxy
   ```

3. **Access the web interface**:
   Open your browser to `http://localhost:3000`

### Option 2: Local Python Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd <path/to>/podcast-rss-proxy
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**:
   ```bash
   python app.py
   ```

5. **Access the web interface**:
   Open your browser to `http://localhost:3000`

3. **Add a podcast feed**:
   - Enter the original RSS feed URL in the input field
   - Click "Add Feed"
   - The server will automatically sync the feed and fetch episode metadata

4. **Get your proxied RSS feed**:
   - Click "Copy RSS URL" for any feed
   - Use this URL in your podcast app: `http://localhost:3000/feed/{feed_id}/rss.xml`

## Configuration

### Environment Variables

The application can be configured using environment variables:

```bash
PORT=3000                              # Server port (default: 3000)
BASE_URL=http://localhost:3000         # Base URL for RSS feeds and episode links
DOWNLOADS_DIR=./downloads              # Directory for cached episodes
DB_PATH=./podcasts.db                  # Database file path
SYNC_INTERVAL=3600                     # Background sync interval in seconds
DOWNLOAD_ON_DEMAND=True                # Enable on-demand downloading
```

### Reverse Proxy Setup

When running behind a reverse proxy (nginx, Traefik, etc.), set `BASE_URL` to your public URL:

```bash
# In docker-compose.yml
environment:
  - BASE_URL=https://podcasts.example.com

# Or when running manually
export BASE_URL=https://podcasts.example.com
python app.py
```

This ensures all RSS feed URLs and episode links use your public domain instead of localhost.

### Local Configuration

Edit `config.py` to customize default settings:

```python
PORT = 3000                    # Server port
BASE_URL = 'http://localhost:3000'  # Base URL for generated feeds
DOWNLOADS_DIR = './downloads'  # Where to store cached episodes
DB_PATH = './podcasts.db'      # SQLite database path
SYNC_INTERVAL = 3600           # Sync interval in seconds (1 hour)
DOWNLOAD_ON_DEMAND = True      # Download episodes when accessed
```

You can also use environment variables:
```bash
export PORT=8080
export BASE_URL=http://your-domain.com:8080
python app.py
```

## API Endpoints

### Feeds
- `GET /api/feeds` - List all feeds
- `POST /api/feeds` - Add a new feed (body: `{"url": "..."}`)
- `GET /api/feeds/{id}` - Get feed details with episodes
- `DELETE /api/feeds/{id}` - Delete a feed
- `POST /api/feeds/{id}/sync` - Sync a specific feed
- `POST /api/sync-all` - Sync all feeds

### Episodes
- `POST /api/episodes/{id}/download` - Download an episode
- `GET /episode/{id}/download` - Stream/download episode file

### RSS
- `GET /feed/{id}/rss.xml` - Get regenerated RSS feed

## Project Structure

```
podcast-rss-proxy/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── database.py         # SQLite database layer
├── rss_sync.py         # RSS feed syncing logic
├── downloader.py       # Episode download manager
├── rss_generator.py    # RSS feed generator
├── requirements.txt    # Python dependencies
├── static/
│   └── index.html      # Web UI
├── downloads/          # Cached episode files (created automatically)
└── podcasts.db         # SQLite database (created automatically)
```

## How It Works

1. **Add Feed**: When you add a podcast RSS feed URL, the server fetches and parses it
2. **Sync**: Episode metadata is stored in SQLite database
3. **Cache**: When an episode is accessed, it's downloaded on-demand and cached locally
4. **Serve**: The regenerated RSS feed points to your local server for episode files
5. **Background Sync**: Every hour, all feeds are synced to check for new episodes

## Use Cases

- **Privacy**: Keep your podcast listening habits private
- **Offline Access**: Cache episodes for offline listening
- **Bandwidth Control**: Download episodes on your schedule
- **Archive**: Keep a local archive of podcast episodes
- **Custom Processing**: Modify or process episodes before serving

## Requirements

- Python 3.7+
- Flask
- feedparser
- requests
- xmltodict

## License

MIT
