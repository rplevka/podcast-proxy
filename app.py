from flask import Flask, request, jsonify, send_file, Response
import threading
import time
import os
import requests
import urllib3
from database import PodcastDatabase
from rss_sync import RSSSync
from downloader import Downloader
from rss_generator import RSSGenerator
from download_manager import DownloadManager
from file_watcher import start_file_watcher
import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

db = PodcastDatabase(config.DB_PATH)
rss_sync = RSSSync(db)
download_manager = DownloadManager()
downloader = Downloader(db, download_manager)
rss_generator = RSSGenerator(db)

file_observer = start_file_watcher(db)

@app.route('/')
def index():
    return send_file('static/index.html')

@app.route('/api/feeds', methods=['GET'])
def get_feeds():
    feeds = db.get_feeds()
    return jsonify(feeds)

@app.route('/api/feeds', methods=['POST'])
def add_feed():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        feed_id = db.add_feed(url)
        rss_sync.sync_feed(feed_id)
        feed = db.get_feed(feed_id)
        return jsonify(feed), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feeds/<int:feed_id>', methods=['GET'])
def get_feed(feed_id):
    feed = db.get_feed(feed_id)
    if not feed:
        return jsonify({'error': 'Feed not found'}), 404
    
    episodes = db.get_episodes(feed_id)
    feed['episodes'] = episodes
    return jsonify(feed)

@app.route('/api/feeds/<int:feed_id>', methods=['DELETE'])
def delete_feed(feed_id):
    db.delete_feed(feed_id)
    return '', 204

@app.route('/api/feeds/<int:feed_id>/sync', methods=['POST'])
def sync_feed(feed_id):
    try:
        result = rss_sync.sync_feed(feed_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync-all', methods=['POST'])
def sync_all():
    try:
        results = rss_sync.sync_all_feeds()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/episodes/<int:episode_id>/download', methods=['POST'])
def download_episode_api(episode_id):
    try:
        def download_in_background():
            try:
                downloader.download_episode(episode_id)
            except Exception as e:
                print(f"Background download error: {e}")
        
        thread = threading.Thread(target=download_in_background, daemon=True)
        thread.start()
        return jsonify({'success': True, 'downloading': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-progress', methods=['GET'])
def get_download_progress():
    return jsonify(download_manager.get_all_progress())

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({'base_url': config.BASE_URL})

@app.route('/api/cleanup', methods=['POST'])
def cleanup_database():
    try:
        feeds = db.get_feeds()
        total_checked = 0
        total_marked_missing = 0
        
        for feed in feeds:
            episodes = db.get_episodes(feed['id'])
            
            for episode in episodes:
                if episode['downloaded'] and episode['local_path']:
                    total_checked += 1
                    
                    if not os.path.exists(episode['local_path']):
                        conn = db.get_connection()
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE episodes 
                            SET downloaded = 0, local_path = NULL, file_size = NULL
                            WHERE id = ?
                        ''', (episode['id'],))
                        conn.commit()
                        conn.close()
                        total_marked_missing += 1
        
        return jsonify({
            'success': True,
            'checked': total_checked,
            'cleaned': total_marked_missing
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feed/<int:feed_id>/rss.xml', methods=['GET'])
def get_rss_feed(feed_id):
    try:
        xml = rss_generator.generate_feed(feed_id)
        return Response(xml, mimetype='application/xml; charset=utf-8')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/episode/<int:episode_id>/download', methods=['GET'])
def serve_episode(episode_id):
    try:
        episode = db.get_episode(episode_id)
        if not episode:
            return jsonify({'error': 'Episode not found'}), 404
        
        if episode['downloaded'] and episode['local_path'] and os.path.exists(episode['local_path']):
            return send_file(episode['local_path'], as_attachment=False)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ferorss/1.0)'
        }
        response = requests.get(episode['original_url'], stream=True, verify=False, headers=headers)
        response.raise_for_status()
        
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return Response(generate(), mimetype='audio/mpeg', headers={
            'Content-Type': response.headers.get('Content-Type', 'audio/mpeg'),
            'Content-Length': response.headers.get('Content-Length', ''),
            'Accept-Ranges': 'bytes'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

def background_sync():
    while True:
        time.sleep(config.SYNC_INTERVAL)
        print("Running background sync...")
        try:
            rss_sync.sync_all_feeds()
        except Exception as e:
            print(f"Background sync error: {e}")

if __name__ == '__main__':
    sync_thread = threading.Thread(target=background_sync, daemon=True)
    sync_thread.start()
    
    print(f"Starting Podcast RSS Proxy on port {config.PORT}")
    print(f"Base URL: {config.BASE_URL}")
    app.run(host='0.0.0.0', port=config.PORT, debug=True)
