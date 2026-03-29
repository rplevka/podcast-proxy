import time
from typing import Optional, List, Dict, Any
from models import db, Feed, Episode, DownloadStatus
from email.utils import parsedate_to_datetime

class PodcastDatabase:
    def __init__(self, db_path: str = None):
        pass
    
    def add_feed(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        if metadata is None:
            metadata = {}
        
        feed = Feed.query.filter_by(original_url=url).first()
        
        if feed:
            feed.title = metadata.get('title') or feed.title
            feed.description = metadata.get('description') or feed.description
            feed.image_url = metadata.get('image_url') or feed.image_url
            if 'price' in metadata:
                feed.price = metadata.get('price')
            if 'currency' in metadata:
                feed.currency = metadata.get('currency')
        else:
            feed = Feed(
                original_url=url,
                title=metadata.get('title'),
                description=metadata.get('description'),
                image_url=metadata.get('image_url'),
                price=metadata.get('price'),
                currency=metadata.get('currency', 'USD')
            )
            db.session.add(feed)
        
        db.session.commit()
        return feed.id
    
    def get_feeds(self) -> List[Dict[str, Any]]:
        feeds = Feed.query.order_by(Feed.created_at.desc()).all()
        return [feed.to_dict() for feed in feeds]
    
    def get_feed(self, feed_id: int) -> Optional[Dict[str, Any]]:
        feed = Feed.query.get(feed_id)
        return feed.to_dict() if feed else None
    
    def get_feed_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        feed = Feed.query.filter_by(original_url=url).first()
        return feed.to_dict() if feed else None
    
    def delete_feed(self, feed_id: int):
        feed = Feed.query.get(feed_id)
        if feed:
            db.session.delete(feed)
            db.session.commit()
    
    def update_feed_sync(self, feed_id: int):
        feed = Feed.query.get(feed_id)
        if feed:
            feed.last_synced = int(time.time())
            db.session.commit()
    
    def add_episode(self, feed_id: int, episode: Dict[str, Any]):
        existing = Episode.query.filter_by(
            feed_id=feed_id, 
            guid=episode['guid']
        ).first()
        
        if existing:
            existing.title = episode.get('title')
            existing.description = episode.get('description')
            existing.pub_date = episode.get('pub_date')
            existing.duration = episode.get('duration')
            existing.original_url = episode['url']
            existing.file_size = episode.get('file_size')
        else:
            new_episode = Episode(
                feed_id=feed_id,
                guid=episode['guid'],
                title=episode.get('title'),
                description=episode.get('description'),
                pub_date=episode.get('pub_date'),
                duration=episode.get('duration'),
                original_url=episode['url'],
                file_size=episode.get('file_size')
            )
            db.session.add(new_episode)
        
        db.session.commit()
    
    def get_episodes(self, feed_id: int) -> List[Dict[str, Any]]:
        episodes = Episode.query.filter_by(feed_id=feed_id).all()
        episode_dicts = [ep.to_dict() for ep in episodes]
        
        def get_sort_key(ep):
            try:
                if ep.get('pub_date'):
                    return parsedate_to_datetime(ep['pub_date']).timestamp()
                return 0
            except:
                return 0
        
        episode_dicts.sort(key=get_sort_key, reverse=True)
        return episode_dicts
    
    def get_episode(self, episode_id: int) -> Optional[Dict[str, Any]]:
        episode = Episode.query.get(episode_id)
        return episode.to_dict() if episode else None
    
    def get_episode_by_guid(self, feed_id: int, guid: str) -> Optional[Dict[str, Any]]:
        episode = Episode.query.filter_by(feed_id=feed_id, guid=guid).first()
        return episode.to_dict() if episode else None
    
    def mark_episode_downloading(self, episode_id: int):
        episode = Episode.query.get(episode_id)
        if episode:
            episode.download_status = DownloadStatus.IN_PROGRESS
            db.session.commit()
    
    def mark_episode_downloaded(self, episode_id: int, local_path: str, file_size: int):
        episode = Episode.query.get(episode_id)
        if episode:
            episode.downloaded = 1
            episode.download_status = DownloadStatus.DOWNLOADED
            episode.local_path = local_path
            episode.file_size = file_size
            db.session.commit()
    
    def mark_episode_download_failed(self, episode_id: int):
        episode = Episode.query.get(episode_id)
        if episode:
            episode.download_status = DownloadStatus.NOT_DOWNLOADED
            db.session.commit()
    
    def get_in_progress_downloads(self) -> List[Dict[str, Any]]:
        episodes = Episode.query.filter_by(download_status=DownloadStatus.IN_PROGRESS).all()
        return [ep.to_dict() for ep in episodes]
    
    def get_connection(self):
        return db.session
