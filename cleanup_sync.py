import os
from database import PodcastDatabase
import config

def sync_database_with_filesystem():
    """
    Sync database with filesystem - mark episodes as not downloaded if files don't exist
    """
    db = PodcastDatabase(config.DB_PATH)
    
    feeds = db.get_feeds()
    total_checked = 0
    total_marked_missing = 0
    
    for feed in feeds:
        episodes = db.get_episodes(feed['id'])
        
        for episode in episodes:
            if episode['downloaded'] and episode['local_path']:
                total_checked += 1
                
                if not os.path.exists(episode['local_path']):
                    print(f"File missing: {episode['local_path']}")
                    print(f"  Episode: {episode['title']}")
                    
                    conn = db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE episodes 
                        SET downloaded = 0, local_p                        SET d                                    SET downloa               (e                        SET downlo  c      mm                        SET downloaded = 0, local_p                        SET d       rk      si                        SET downloadedte:                             tal                    
                            do   oa                     ss                            do   oa                   atabase_with_filesystem()
