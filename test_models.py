import pytest
import time
from datetime import datetime, UTC
from flask import Flask
from models import db, Feed, Episode, DownloadStatus


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Provide an application context for tests."""
    with app.app_context():
        yield


class TestDownloadStatus:
    """Test DownloadStatus enum constants."""
    
    def test_download_status_values(self):
        """Test that DownloadStatus has correct values."""
        assert DownloadStatus.NOT_DOWNLOADED == 0
        assert DownloadStatus.DOWNLOADED == 1
        assert DownloadStatus.IN_PROGRESS == 2
    
    def test_download_status_uniqueness(self):
        """Test that all DownloadStatus values are unique."""
        values = [
            DownloadStatus.NOT_DOWNLOADED,
            DownloadStatus.DOWNLOADED,
            DownloadStatus.IN_PROGRESS
        ]
        assert len(values) == len(set(values))


class TestFeedModel:
    """Test Feed model functionality."""
    
    def test_feed_creation(self, app_context):
        """Test creating a Feed instance."""
        feed = Feed(
            original_url='https://example.com/feed.xml',
            title='Test Podcast',
            description='A test podcast',
            image_url='https://example.com/image.jpg'
        )
        db.session.add(feed)
        db.session.commit()
        
        assert feed.id is not None
        assert feed.original_url == 'https://example.com/feed.xml'
        assert feed.title == 'Test Podcast'
        assert feed.description == 'A test podcast'
        assert feed.image_url == 'https://example.com/image.jpg'
    
    def test_feed_created_at_auto_set(self, app_context):
        """Test that created_at is automatically set."""
        before = int(datetime.now(UTC).timestamp())
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        after = int(datetime.now(UTC).timestamp())
        
        assert feed.created_at is not None
        assert before <= feed.created_at <= after
    
    def test_feed_unique_url_constraint(self, app_context):
        """Test that original_url must be unique."""
        feed1 = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed1)
        db.session.commit()
        
        feed2 = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed2)
        
        with pytest.raises(Exception):
            db.session.commit()
    
    def test_feed_to_dict(self, app_context):
        """Test Feed.to_dict() method."""
        feed = Feed(
            original_url='https://example.com/feed.xml',
            title='Test Podcast',
            description='A test podcast',
            image_url='https://example.com/image.jpg',
            last_synced=1234567890
        )
        db.session.add(feed)
        db.session.commit()
        
        feed_dict = feed.to_dict()
        
        assert feed_dict['id'] == feed.id
        assert feed_dict['original_url'] == 'https://example.com/feed.xml'
        assert feed_dict['title'] == 'Test Podcast'
        assert feed_dict['description'] == 'A test podcast'
        assert feed_dict['image_url'] == 'https://example.com/image.jpg'
        assert feed_dict['last_synced'] == 1234567890
        assert feed_dict['created_at'] == feed.created_at
    
    def test_feed_nullable_fields(self, app_context):
        """Test that optional fields can be None."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        assert feed.title is None
        assert feed.description is None
        assert feed.image_url is None
        assert feed.last_synced is None
    
    def test_feed_url_required(self, app_context):
        """Test that original_url is required."""
        feed = Feed(title='Test Podcast')
        db.session.add(feed)
        
        with pytest.raises(Exception):
            db.session.commit()


class TestEpisodeModel:
    """Test Episode model functionality."""
    
    def test_episode_creation(self, app_context):
        """Test creating an Episode instance."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(
            feed_id=feed.id,
            guid='episode-123',
            title='Episode 1',
            description='First episode',
            pub_date='Mon, 01 Jan 2024 00:00:00 GMT',
            duration='00:30:00',
            original_url='https://example.com/episode1.mp3'
        )
        db.session.add(episode)
        db.session.commit()
        
        assert episode.id is not None
        assert episode.feed_id == feed.id
        assert episode.guid == 'episode-123'
        assert episode.title == 'Episode 1'
    
    def test_episode_defaults(self, app_context):
        """Test Episode default values."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(feed_id=feed.id, guid='episode-123')
        db.session.add(episode)
        db.session.commit()
        
        assert episode.downloaded == 0
        assert episode.download_status == 0
        assert episode.created_at is not None
    
    def test_episode_download_status_values(self, app_context):
        """Test setting different download_status values."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(feed_id=feed.id, guid='episode-123')
        db.session.add(episode)
        db.session.commit()
        
        episode.download_status = DownloadStatus.IN_PROGRESS
        db.session.commit()
        assert episode.download_status == DownloadStatus.IN_PROGRESS
        
        episode.download_status = DownloadStatus.DOWNLOADED
        db.session.commit()
        assert episode.download_status == DownloadStatus.DOWNLOADED
    
    def test_episode_unique_feed_guid_constraint(self, app_context):
        """Test that feed_id + guid must be unique."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode1 = Episode(feed_id=feed.id, guid='episode-123')
        db.session.add(episode1)
        db.session.commit()
        
        episode2 = Episode(feed_id=feed.id, guid='episode-123')
        db.session.add(episode2)
        
        with pytest.raises(Exception):
            db.session.commit()
    
    def test_episode_same_guid_different_feeds(self, app_context):
        """Test that same guid can exist in different feeds."""
        feed1 = Feed(original_url='https://example.com/feed1.xml')
        feed2 = Feed(original_url='https://example.com/feed2.xml')
        db.session.add_all([feed1, feed2])
        db.session.commit()
        
        episode1 = Episode(feed_id=feed1.id, guid='episode-123')
        episode2 = Episode(feed_id=feed2.id, guid='episode-123')
        db.session.add_all([episode1, episode2])
        db.session.commit()
        
        assert episode1.id != episode2.id
        assert episode1.guid == episode2.guid
    
    def test_episode_to_dict(self, app_context):
        """Test Episode.to_dict() method."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(
            feed_id=feed.id,
            guid='episode-123',
            title='Episode 1',
            description='First episode',
            pub_date='Mon, 01 Jan 2024 00:00:00 GMT',
            duration='00:30:00',
            original_url='https://example.com/episode1.mp3',
            local_path='/downloads/episode1.mp3',
            file_size=1024000,
            downloaded=1,
            download_status=DownloadStatus.DOWNLOADED
        )
        db.session.add(episode)
        db.session.commit()
        
        episode_dict = episode.to_dict()
        
        assert episode_dict['id'] == episode.id
        assert episode_dict['feed_id'] == feed.id
        assert episode_dict['guid'] == 'episode-123'
        assert episode_dict['title'] == 'Episode 1'
        assert episode_dict['description'] == 'First episode'
        assert episode_dict['pub_date'] == 'Mon, 01 Jan 2024 00:00:00 GMT'
        assert episode_dict['duration'] == '00:30:00'
        assert episode_dict['original_url'] == 'https://example.com/episode1.mp3'
        assert episode_dict['local_path'] == '/downloads/episode1.mp3'
        assert episode_dict['file_size'] == 1024000
        assert episode_dict['downloaded'] == 1
        assert episode_dict['download_status'] == DownloadStatus.DOWNLOADED
        assert episode_dict['created_at'] == episode.created_at
    
    def test_episode_required_fields(self, app_context):
        """Test that feed_id and guid are required."""
        episode = Episode(title='Episode 1')
        db.session.add(episode)
        
        with pytest.raises(Exception):
            db.session.commit()


class TestFeedEpisodeRelationship:
    """Test relationship between Feed and Episode models."""
    
    def test_feed_episodes_relationship(self, app_context):
        """Test that Feed.episodes relationship works."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode1 = Episode(feed_id=feed.id, guid='episode-1')
        episode2 = Episode(feed_id=feed.id, guid='episode-2')
        db.session.add_all([episode1, episode2])
        db.session.commit()
        
        assert len(feed.episodes) == 2
        assert episode1 in feed.episodes
        assert episode2 in feed.episodes
    
    def test_episode_feed_backref(self, app_context):
        """Test that Episode.feed backref works."""
        feed = Feed(original_url='https://example.com/feed.xml', title='Test Podcast')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(feed_id=feed.id, guid='episode-1')
        db.session.add(episode)
        db.session.commit()
        
        assert episode.feed.id == feed.id
        assert episode.feed.title == 'Test Podcast'
    
    def test_cascade_delete(self, app_context):
        """Test that deleting a feed deletes its episodes."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode1 = Episode(feed_id=feed.id, guid='episode-1')
        episode2 = Episode(feed_id=feed.id, guid='episode-2')
        db.session.add_all([episode1, episode2])
        db.session.commit()
        
        feed_id = feed.id
        db.session.delete(feed)
        db.session.commit()
        
        remaining_episodes = Episode.query.filter_by(feed_id=feed_id).all()
        assert len(remaining_episodes) == 0
    
    def test_multiple_feeds_with_episodes(self, app_context):
        """Test multiple feeds each with their own episodes."""
        feed1 = Feed(original_url='https://example.com/feed1.xml', title='Podcast 1')
        feed2 = Feed(original_url='https://example.com/feed2.xml', title='Podcast 2')
        db.session.add_all([feed1, feed2])
        db.session.commit()
        
        ep1_f1 = Episode(feed_id=feed1.id, guid='ep1')
        ep2_f1 = Episode(feed_id=feed1.id, guid='ep2')
        ep1_f2 = Episode(feed_id=feed2.id, guid='ep1')
        db.session.add_all([ep1_f1, ep2_f1, ep1_f2])
        db.session.commit()
        
        assert len(feed1.episodes) == 2
        assert len(feed2.episodes) == 1
        assert ep1_f1.feed.title == 'Podcast 1'
        assert ep1_f2.feed.title == 'Podcast 2'


class TestModelQueries:
    """Test common query patterns."""
    
    def test_query_episodes_by_download_status(self, app_context):
        """Test querying episodes by download_status."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        ep1 = Episode(feed_id=feed.id, guid='ep1', download_status=DownloadStatus.NOT_DOWNLOADED)
        ep2 = Episode(feed_id=feed.id, guid='ep2', download_status=DownloadStatus.IN_PROGRESS)
        ep3 = Episode(feed_id=feed.id, guid='ep3', download_status=DownloadStatus.DOWNLOADED)
        ep4 = Episode(feed_id=feed.id, guid='ep4', download_status=DownloadStatus.IN_PROGRESS)
        db.session.add_all([ep1, ep2, ep3, ep4])
        db.session.commit()
        
        in_progress = Episode.query.filter_by(download_status=DownloadStatus.IN_PROGRESS).all()
        assert len(in_progress) == 2
        assert ep2 in in_progress
        assert ep4 in in_progress
    
    def test_query_downloaded_episodes(self, app_context):
        """Test querying downloaded episodes."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        ep1 = Episode(feed_id=feed.id, guid='ep1', downloaded=0)
        ep2 = Episode(feed_id=feed.id, guid='ep2', downloaded=1)
        ep3 = Episode(feed_id=feed.id, guid='ep3', downloaded=1)
        db.session.add_all([ep1, ep2, ep3])
        db.session.commit()
        
        downloaded = Episode.query.filter_by(downloaded=1).all()
        assert len(downloaded) == 2
    
    def test_query_feed_by_url(self, app_context):
        """Test querying feed by URL."""
        feed = Feed(original_url='https://example.com/feed.xml', title='Test')
        db.session.add(feed)
        db.session.commit()
        
        found = Feed.query.filter_by(original_url='https://example.com/feed.xml').first()
        assert found is not None
        assert found.title == 'Test'
    
    def test_query_episode_by_guid_and_feed(self, app_context):
        """Test querying episode by guid and feed_id."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(feed_id=feed.id, guid='unique-guid', title='Test Episode')
        db.session.add(episode)
        db.session.commit()
        
        found = Episode.query.filter_by(feed_id=feed.id, guid='unique-guid').first()
        assert found is not None
        assert found.title == 'Test Episode'


class TestModelEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_feed_with_long_url(self, app_context):
        """Test feed with maximum length URL."""
        long_url = 'https://example.com/' + 'a' * 470
        feed = Feed(original_url=long_url)
        db.session.add(feed)
        db.session.commit()
        
        assert feed.original_url == long_url
    
    def test_episode_with_long_guid(self, app_context):
        """Test episode with long GUID."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        long_guid = 'guid-' + 'x' * 490
        episode = Episode(feed_id=feed.id, guid=long_guid)
        db.session.add(episode)
        db.session.commit()
        
        assert episode.guid == long_guid
    
    def test_episode_with_large_file_size(self, app_context):
        """Test episode with large file size."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(feed_id=feed.id, guid='ep1', file_size=2147483647)
        db.session.add(episode)
        db.session.commit()
        
        assert episode.file_size == 2147483647
    
    def test_feed_update_last_synced(self, app_context):
        """Test updating feed's last_synced timestamp."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        assert feed.last_synced is None
        
        timestamp = int(time.time())
        feed.last_synced = timestamp
        db.session.commit()
        
        assert feed.last_synced == timestamp
    
    def test_episode_update_download_fields(self, app_context):
        """Test updating episode download-related fields."""
        feed = Feed(original_url='https://example.com/feed.xml')
        db.session.add(feed)
        db.session.commit()
        
        episode = Episode(feed_id=feed.id, guid='ep1')
        db.session.add(episode)
        db.session.commit()
        
        episode.download_status = DownloadStatus.IN_PROGRESS
        db.session.commit()
        assert episode.download_status == DownloadStatus.IN_PROGRESS
        
        episode.downloaded = 1
        episode.download_status = DownloadStatus.DOWNLOADED
        episode.local_path = '/downloads/ep1.mp3'
        episode.file_size = 5000000
        db.session.commit()
        
        assert episode.downloaded == 1
        assert episode.download_status == DownloadStatus.DOWNLOADED
        assert episode.local_path == '/downloads/ep1.mp3'
        assert episode.file_size == 5000000
