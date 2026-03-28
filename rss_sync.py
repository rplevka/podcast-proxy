import feedparser
import requests
from typing import Dict, Any, List
from database import PodcastDatabase

class RSSSync:
    def __init__(self, database: PodcastDatabase):
        self.db = database
    
    def sync_feed(self, feed_id: int) -> Dict[str, Any]:
        feed = self.db.get_feed(feed_id)
        if not feed:
            raise ValueError(f"Feed {feed_id} not found")
        
        print(f"Syncing feed: {feed['original_url']}")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; ferorss/1.0)'
            }
            response = requests.get(feed['original_url'], timeout=30, verify=False, headers=headers)
            response.raise_for_status()
            
            parsed = feedparser.parse(response.content)
            
            if parsed.bozo and not parsed.entries:
                raise ValueError(f"Invalid RSS feed: {parsed.bozo_exception}")
            
            feed_metadata = {
                'title': parsed.feed.get('title'),
                'description': parsed.feed.get('description') or parsed.feed.get('subtitle'),
                'image_url': self._extract_image_url(parsed.feed)
            }
            
            self.db.add_feed(feed['original_url'], feed_metadata)
            
            episode_count = 0
            for entry in parsed.entries:
                enclosure = self._get_enclosure(entry)
                if not enclosure:
                    continue
                
                episode = {
                    'guid': entry.get('id') or entry.get('link') or enclosure['url'],
                    'title': entry.get('title'),
                    'description': entry.get('summary') or entry.get('description'),
                    'pub_date': entry.get('published') or entry.get('updated'),
                    'duration': self._get_duration(entry),
                    'url': enclosure['url'],
                    'file_size': enclosure.get('length')
                }
                
                self.db.add_episode(feed_id, episode)
                episode_count += 1
            
            self.db.update_feed_sync(feed_id)
            print(f"Synced {episode_count} episodes for feed {feed_id}")
            
            return {'success': True, 'episode_count': episode_count}
        
        except Exception as e:
            print(f"Error syncing feed {feed_id}: {str(e)}")
            raise
    
    def sync_all_feeds(self) -> List[Dict[str, Any]]:
        feeds = self.db.get_feeds()
        results = []
        
        for feed in feeds:
            try:
                result = self.sync_feed(feed['id'])
                results.append({'feed_id': feed['id'], **result})
            except Exception as e:
                results.append({
                    'feed_id': feed['id'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _extract_image_url(self, feed: Any) -> str:
        if hasattr(feed, 'image') and 'href' in feed.image:
            return feed.image.href
        if 'itunes_image' in feed:
            if isinstance(feed.itunes_image, dict):
                return feed.itunes_image.get('href')
            return feed.itunes_image
        return None
    
    def _get_enclosure(self, entry: Any) -> Dict[str, Any]:
        if hasattr(entry, 'enclosures') and entry.enclosures:
            enclosure = entry.enclosures[0]
            return {
                'url': enclosure.get('href') or enclosure.get('url'),
                'length': int(enclosure.get('length', 0)) if enclosure.get('length') else None,
                'type': enclosure.get('type')
            }
        return None
    
    def _get_duration(self, entry: Any) -> str:
        if 'itunes_duration' in entry:
            return entry.itunes_duration
        return None
