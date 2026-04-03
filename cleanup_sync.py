import os
from database import PodcastDatabase
from models import Episode, DownloadStatus, db
import config

def sync_database_with_filesystem():
    """
    Sync database with filesystem - mark episodes as not downloaded if files don't exist
    """
    podcast_db = PodcastDatabase()
    
    feeds = podcast_db.get_feeds()
    total_checked = 0
    total_marked_missing = 0
    
    for feed in feeds:
        episodes = podcast_db.get_episodes(feed['id'])
        
        for episode in episodes:
            if episode['downloaded'] and episode['local_path']:
                total_checked += 1
                
                if not os.path.exists(episode['local_path']):
                    print(f"File missing: {episode['local_path']}")
                    print(f"  Episode: {episode['title']}")
                    
                    ep = db.session.get(Episode, episode['id'])
                    if ep:
                        ep.downloaded = 0
                        ep.download_status = DownloadStatus.NOT_DOWNLOADED
                        ep.local_path = None
                        ep.file_size = None
                        total_marked_missing += 1
    
    db.session.commit()
    
    print(f"\nSync complete:")
    print(f"  Total episodes checked: {total_checked}")
    print(f"  Episodes marked as missing: {total_marked_missing}")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        sync_database_with_filesystem()
