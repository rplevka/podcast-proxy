import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from database import PodcastDatabase
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
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, title FROM episodes WHERE local_path = ? AND downloaded = 1",
            (deleted_path,)
        )
        
        episode = cursor.fetchone()
        
        if episode:
            episode_id = episode["id"]
            episode_title = episode["title"]
            
            cursor.execute(
                "UPDATE episodes SET downloaded = 0, local_path = NULL, file_size = NULL WHERE id = ?",
                (episode_id,)
            )
            
            conn.commit()
            print(f"  Marked episode as not downloaded: {episode_title}")
        else:
            print(f"  No matching episode found in database for path: {deleted_path}")
        
        conn.close()

def start_file_watcher(database):
    if not os.path.exists(config.DOWNLOADS_DIR):
        os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
    
    event_handler = DownloadsDirHandler(database)
    observer = Observer()
    observer.schedule(event_handler, config.DOWNLOADS_DIR, recursive=True)
    observer.start()
    
    print(f"File watcher started for: {config.DOWNLOADS_DIR}")
    return observer
