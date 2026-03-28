import os
import requests
from pathlib import Path
from typing import Optional
from database import PodcastDatabase
import config

class Downloader:
    def __init__(self, database: PodcastDatabase, download_manager=None):
        self.db = database
        self.download_manager = download_manager
        self.ensure_downloads_dir()
    
    def ensure_downloads_dir(self):
        Path(config.DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)
    
    def download_episode(self, episode_id: int) -> str:
        episode = self.db.get_episode(episode_id)
        if not episode:
            raise ValueError(f"Episode {episode_id} not found")
        
        if episode['downloaded'] and episode['local_path'] and os.path.exists(episode['local_path']):
            print(f"Episode {episode_id} already downloaded")
            return episode['local_path']
        
        print(f"Downloading episode {episode_id}: {episode['title']}")
        
        feed_dir = os.path.join(config.DOWNLOADS_DIR, str(episode['feed_id']))
        os.makedirs(feed_dir, exist_ok=True)
        
        ext = Path(episode['original_url']).suffix or '.mp3'
        if '?' in ext:
            ext = ext.split('?')[0]
        
        filename = f"{episode_id}_{int(os.times().elapsed * 1000)}{ext}"
        local_path = os.path.join(feed_dir, filename)
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ferorss/1.0)'
            }
            response = requests.get(episode['original_url'], stream=True, timeout=60, verify=False, headers=headers)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            if self.download_manager and total_size > 0:
                self.download_manager.start_download(episode_id, total_size)
            
            downloaded = 0
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if self.download_manager:
                            self.download_manager.update_progress(episode_id, downloaded)
            
            file_size = os.path.getsize(local_path)
            self.db.mark_episode_downloaded(episode_id, local_path, file_size)
            
            if self.download_manager:
                self.download_manager.finish_download(episode_id)
            
            print(f"Downloaded episode {episode_id} to {local_path}")
            return local_path
        
        except Exception as e:
            if os.path.exists(local_path):
                os.remove(local_path)
            print(f"Error downloading episode {episode_id}: {str(e)}")
            raise
    
    def get_episode_file(self, episode_id: int) -> str:
        episode = self.db.get_episode(episode_id)
        if not episode:
            raise ValueError(f"Episode {episode_id} not found")
        
        if episode['downloaded'] and episode['local_path'] and os.path.exists(episode['local_path']):
            return episode['local_path']
        
        if config.DOWNLOAD_ON_DEMAND:
            return self.download_episode(episode_id)
        
        raise ValueError(f"Episode {episode_id} not downloaded and on-demand downloading is disabled")
