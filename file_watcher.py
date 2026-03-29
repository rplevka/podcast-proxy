import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from database import PodcastDatabase
from models import Episode, DownloadStatus
import config

class DownloadsDirHandler(FileSystemEventHandler):
    def __init__(self, database):
        self.db = database
        super().__init__()
    
    def on_deleted(self, event):
        if event.is_directory:
            return
        
        deleted_path = event.src_path
        print(f"File deleted: {deleted_path}")
        
        episode = Episode.query.filter_by(local_path=deleted_path, downloaded=1).first()
        
        if episode:
            episode_title = episode.title
            episode.downloaded = 0
            episode.download_status = DownloadStatus.NOT_DOWNLOADED
            episode.local_path = None
            episode.file_size = None
            
            from models import db
            db.session.commit()
            print(f"  Marked episode as not downloaded: {episode_title}")
        else:
            print(f"  No matching episode found in database for path: {deleted_path}")

def start_file_watcher(database):
    if not os.path.exists(config.DOWNLOADS_DIR):
        os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
    
    event_handler = DownloadsDirHandler(database)
    observer = Observer()
    observer.schedule(event_handler, config.DOWNLOADS_DIR, recursive=True)
    observer.start()
    
    print(f"File watcher started for: {config.DOWNLOADS_DIR}")
    return observer
