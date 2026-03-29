import os

PORT = int(os.getenv('PORT', '3000'))
BASE_URL = os.getenv('BASE_URL', f'http://localhost:{PORT}')
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', './downloads')
DB_PATH = os.getenv('DB_PATH', './podcasts.db')
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '3600'))
DOWNLOAD_ON_DEMAND = os.getenv('DOWNLOAD_ON_DEMAND', 'True').lower() in ('true', '1', 'yes')
MOTD = os.getenv('MOTD', 'Podcast Proxy')
