import sqlite3
import time
from typing import Optional, List, Dict, Any

class PodcastDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                image_url TEXT,
                last_synced INTEGER,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                guid TEXT NOT NULL,
                title TEXT,
                description TEXT,
                pub_date TEXT,
                duration TEXT,
                original_url TEXT,
                local_path TEXT,
                file_size INTEGER,
                downloaded INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE,
                UNIQUE(feed_id, guid)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_feed_id ON episodes(feed_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_episodes_guid ON episodes(guid)')
        
        conn.commit()
        conn.close()
    
    def add_feed(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        if metadata is None:
            metadata = {}
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feeds (original_url, title, description, image_url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(original_url) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                image_url = excluded.image_url
        ''', (
            url,
            metadata.get('title'),
            metadata.get('description'),
            metadata.get('image_url')
        ))
        
        feed_id = cursor.lastrowid
        if feed_id == 0:
            cursor.execute('SELECT id FROM feeds WHERE original_url = ?', (url,))
            feed_id = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        return feed_id
    
    def get_feeds(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM feeds ORDER BY created_at DESC')
        feeds = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return feeds
    
    def get_feed(self, feed_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM feeds WHERE id = ?', (feed_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_feed_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM feeds WHERE original_url = ?', (url,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def delete_feed(self, feed_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM feeds WHERE id = ?', (feed_id,))
        conn.commit()
        conn.close()
    
    def update_feed_sync(self, feed_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE feeds SET last_synced = ? WHERE id = ?', 
                      (int(time.time()), feed_id))
        conn.commit()
        conn.close()
    
    def add_episode(self, feed_id: int, episode: Dict[str, Any]):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO episodes (
                feed_id, guid, title, description, pub_date, duration, original_url, file_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(feed_id, guid) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                pub_date = excluded.pub_date,
                duration = excluded.duration,
                original_url = excluded.original_url,
                file_size = excluded.file_size
        ''', (
            feed_id,
            episode['guid'],
            episode.get('title'),
            episode.get('description'),
            episode.get('pub_date'),
            episode.get('duration'),
            episode['url'],
            episode.get('file_size')
        ))
        
        conn.commit()
        conn.close()
    
    def get_episodes(self, feed_id: int) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        # Get all episodes and sort in Python since RFC 2822 parsing in SQLite is complex
        cursor.execute('SELECT * FROM episodes WHERE feed_id = ?', (feed_id,))
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Sort by pub_date (newest first), handling RFC 2822 format
        from email.utils import parsedate_to_datetime
        def get_sort_key(ep):
            try:
                if ep.get('pub_date'):
                    return parsedate_to_datetime(ep['pub_date']).timestamp()
                return 0
            except:
                return 0
        
        episodes.sort(key=get_sort_key, reverse=True)
        return episodes
    
    def get_episode(self, episode_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM episodes WHERE id = ?', (episode_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_episode_by_guid(self, feed_id: int, guid: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM episodes WHERE feed_id = ? AND guid = ?', 
                      (feed_id, guid))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def mark_episode_downloaded(self, episode_id: int, local_path: str, file_size: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE episodes 
            SET downloaded = 1, local_path = ?, file_size = ?
            WHERE id = ?
        ''', (local_path, file_size, episode_id))
        conn.commit()
        conn.close()
