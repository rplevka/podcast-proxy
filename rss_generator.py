from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from typing import List, Dict, Any
from database import PodcastDatabase
import config

class RSSGenerator:
    def __init__(self, database: PodcastDatabase):
        self.db = database
    
    def generate_feed(self, feed_id: int) -> str:
        feed = self.db.get_feed(feed_id)
        if not feed:
            raise ValueError(f"Feed {feed_id} not found")
        
        episodes = self.db.get_episodes(feed_id)
        
        rss = Element('rss', version='2.0')
        rss.set('xmlns:itunes', 'http://www.itunes.com/dtds/podcast-1.0.dtd')
        rss.set('xmlns:content', 'http://purl.org/rss/1.0/modules/content/')
        
        channel = SubElement(rss, 'channel')
        
        self._add_text_element(channel, 'title', feed.get('title') or 'Untitled Podcast')
        self._add_text_element(channel, 'description', feed.get('description') or '')
        self._add_text_element(channel, 'link', config.BASE_URL)
        
        if feed.get('image_url'):
            image = SubElement(channel, 'image')
            self._add_text_element(image, 'url', feed['image_url'])
            self._add_text_element(image, 'title', feed.get('title') or 'Untitled Podcast')
            self._add_text_element(image, 'link', config.BASE_URL)
        
        for episode in episodes:
            item = SubElement(channel, 'item')
            
            self._add_text_element(item, 'title', episode.get('title') or 'Untitled Episode')
            self._add_text_element(item, 'guid', episode['guid'], isPermaLink='false')
            
            if episode.get('description'):
                self._add_text_element(item, 'description', episode['description'])
            
            if episode.get('pub_date'):
                self._add_text_element(item, 'pubDate', episode['pub_date'])
            
            if episode.get('duration'):
                duration_elem = SubElement(item, '{http://www.itunes.com/dtds/podcast-1.0.dtd}duration')
                duration_elem.text = episode['duration']
            
            episode_url = f"{config.BASE_URL}/episode/{episode['id']}/download"
            
            enclosure = SubElement(item, 'enclosure')
            enclosure.set('url', episode_url)
            enclosure.set('type', 'audio/mpeg')
            if episode.get('file_size'):
                enclosure.set('length', str(episode['file_size']))
            else:
                enclosure.set('length', '0')
        
        return self._prettify_xml(rss)
    
    def _add_text_element(self, parent: Element, tag: str, text: str, **attrs):
        elem = SubElement(parent, tag, **attrs)
        elem.text = text
        return elem
    
    def _prettify_xml(self, elem: Element) -> str:
        rough_string = tostring(elem, encoding='utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
