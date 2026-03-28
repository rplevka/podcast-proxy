import threading
from typing import Dict

class DownloadManager:
    def __init__(self):
        self.downloads: Dict[int, dict] = {}
        self.lock = threading.Lock()
    
    def start_download(self, episode_id: int, total_size: int):
        with self.lock:
            self.downloads[episode_id] = {
                'total': total_size,
                'downloaded': 0,
                'progress': 0
            }
    
    def update_progress(self, episode_id: int, downloaded: int):
        with self.lock:
            if episode_id in self.downloads:
                self.downloads[episode_id]['downloaded'] = downloaded
                total = self.downloads[episode_id]['total']
                if total > 0:
                    self.downloads[episode_id]['progress'] = int((downloaded / total) * 100)
    
    def finish_download(self, episode_id: int):
        with self.lock:
            if episode_id in self.downloads:
                del self.downloads[episode_id]
    
    def get_progress(self, episode_id: int) -> dict:
        with self.lock:
            return self.downloads.get(episode_id, None)
    
    def get_all_progress(self) -> dict:
        with self.lock:
            return dict(self.downloads)
