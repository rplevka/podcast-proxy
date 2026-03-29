import threading
from database import PodcastDatabase
from downloader import Downloader
from download_manager import DownloadManager

def resume_interrupted_downloads(db: PodcastDatabase, downloader: Downloader, flask_app=None):
    in_progress = db.get_in_progress_downloads()
    
    if not in_progress:
        print("No interrupted downloads to resume")
        return
    
    print(f"Found {len(in_progress)} interrupted downloads, resuming...")
    
    for episode in in_progress:
        episode_id = episode['id']
        print(f"Resuming download for episode {episode_id}: {episode['title']}")
        
        def download_in_background(ep_id):
            if flask_app:
                with flask_app.app_context():
                    try:
                        downloader.download_episode(ep_id)
                        print(f"Successfully resumed and completed episode {ep_id}")
                    except Exception as e:
                        print(f"Failed to resume episode {ep_id}: {e}")
            else:
                try:
                    downloader.download_episode(ep_id)
                    print(f"Successfully resumed and completed episode {ep_id}")
                except Exception as e:
                    print(f"Failed to resume episode {ep_id}: {e}")
        
        thread = threading.Thread(target=download_in_background, args=(episode_id,), daemon=True)
        thread.start()
    
    print(f"Started {len(in_progress)} background download threads")
