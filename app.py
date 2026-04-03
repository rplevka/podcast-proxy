from flask import Flask, request, jsonify, send_file, Response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import threading
import time
import os
import requests
import urllib3
from models import db, User, UserRole, InvitationLink, Feed
from database import PodcastDatabase
from rss_sync import RSSSync
from downloader import Downloader
from rss_generator import RSSGenerator
from download_manager import DownloadManager
from file_watcher import start_file_watcher
from audio_validator import AudioValidator
from resume_downloads import resume_interrupted_downloads
from flask_migrate import Migrate
from auth import admin_required, poweruser_required, can_modify_feed
from init_superadmin import run_initialization
import config
import secrets

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config.DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'timeout': 30,
        'check_same_thread': False
    },
    'pool_pre_ping': True,
    'pool_recycle': 3600,
}

db.init_app(app)
migrate = Migrate(app, db)

@app.before_request
def enable_wal_mode():
    """Enable SQLite WAL mode for better concurrency on first request."""
    if not hasattr(app, '_wal_enabled'):
        with app.app_context():
            db.session.execute(db.text('PRAGMA journal_mode=WAL'))
            db.session.execute(db.text('PRAGMA busy_timeout=30000'))
            db.session.execute(db.text('PRAGMA synchronous=NORMAL'))
            db.session.commit()
        app._wal_enabled = True

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = None  # We're using API, not redirects

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    return jsonify({'error': 'Authentication required'}), 401

podcast_db = PodcastDatabase()
rss_sync = RSSSync(podcast_db)
download_manager = DownloadManager()
downloader = Downloader(podcast_db, download_manager)
rss_generator = RSSGenerator(podcast_db)
audio_validator = AudioValidator()

file_observer = None

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return send_file('static/login.html')
    return send_file('static/index.html')

@app.route('/login')
def login_page():
    return send_file('static/login.html')

@app.route('/register')
def register_page():
    return send_file('static/register.html')

@app.route('/api/feeds', methods=['GET'])
def get_feeds():
    feeds = podcast_db.get_feeds()
    
    # Add proxy URL and filter original URL based on permissions
    for feed in feeds:
        # Add proxy URL with user's access token
        if current_user.is_authenticated:
            feed['proxy_url'] = f"{config.BASE_URL}/feed/{current_user.access_token}/rss.xml?feed_id={feed['id']}"
            
            # Hide original URL from non-owners and non-admins
            is_owner = feed.get('owner_id') == current_user.id
            is_admin = current_user.role == UserRole.ADMIN
            
            if not is_owner and not is_admin:
                feed['original_url'] = None  # Hide original URL
        else:
            feed['proxy_url'] = None
            feed['original_url'] = None
    
    return jsonify(feeds)

@app.route('/api/feeds', methods=['POST'])
@poweruser_required
def add_feed():
    data = request.json
    url = data.get('url')
    price = data.get('price')
    currency = data.get('currency', 'USD')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        metadata = {}
        if price is not None:
            metadata['price'] = price
            metadata['currency'] = currency
        
        feed_id = podcast_db.add_feed(url, metadata)
        
        feed_obj = db.session.get(Feed, feed_id)
        if feed_obj:
            feed_obj.owner_id = current_user.id
            db.session.commit()
        
        rss_sync.sync_feed(feed_id)
        feed = podcast_db.get_feed(feed_id)
        return jsonify(feed), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feeds/<int:feed_id>', methods=['GET'])
def get_feed(feed_id):
    feed = podcast_db.get_feed(feed_id)
    if not feed:
        return jsonify({'error': 'Feed not found'}), 404
    
    # Add proxy URL with user's access token
    if current_user.is_authenticated:
        feed['proxy_url'] = f"{config.BASE_URL}/feed/{current_user.access_token}/rss.xml?feed_id={feed['id']}"
        
        # Hide original URL from non-owners and non-admins
        is_owner = feed.get('owner_id') == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        
        if not is_owner and not is_admin:
            feed['original_url'] = None
    else:
        feed['proxy_url'] = None
        feed['original_url'] = None
    
    episodes = podcast_db.get_episodes(feed_id)
    feed['episodes'] = episodes
    return jsonify(feed)

@app.route('/api/feeds/<int:feed_id>', methods=['PATCH'])
@poweruser_required
def update_feed(feed_id):
    feed_obj = db.session.get(Feed, feed_id)
    
    if not feed_obj:
        return jsonify({'error': 'Feed not found'}), 404
    
    if not can_modify_feed(current_user, feed_obj):
        return jsonify({'error': 'You do not have permission to update this feed'}), 403
    
    data = request.json
    new_url = data.get('url')
    
    if not new_url:
        return jsonify({'error': 'URL is required'}), 400
    
    # Update the feed URL
    feed_obj.original_url = new_url
    db.session.commit()
    
    # Trigger background sync
    def sync_in_background():
        with app.app_context():
            try:
                rss_sync.sync_feed(feed_id)
                print(f"Background sync completed for feed {feed_id}")
            except Exception as e:
                print(f"Background sync error for feed {feed_id}: {e}")
    
    thread = threading.Thread(target=sync_in_background, daemon=True)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Feed URL updated and sync started'})

@app.route('/api/feeds/<int:feed_id>', methods=['DELETE'])
@poweruser_required
def delete_feed(feed_id):
    feed_obj = db.session.get(Feed, feed_id)
    
    if not feed_obj:
        return jsonify({'error': 'Feed not found'}), 404
    
    if not can_modify_feed(current_user, feed_obj):
        return jsonify({'error': 'You do not have permission to delete this feed'}), 403
    
    podcast_db.delete_feed(feed_id)
    return '', 204

@app.route('/api/feeds/<int:feed_id>/sync', methods=['POST'])
def sync_feed(feed_id):
    try:
        result = rss_sync.sync_feed(feed_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sync-all', methods=['POST'])
@admin_required
def sync_all_feeds():
    feeds = podcast_db.get_feeds()
    results = []
    for feed in feeds:
        try:
            rss_sync.sync_feed(feed['id'])
            results.append({'feed_id': feed['id'], 'success': True})
        except Exception as e:
            results.append({'feed_id': feed['id'], 'success': False, 'error': str(e)})
    return jsonify(results)

@app.route('/api/episodes/<int:episode_id>/download', methods=['POST'])
def download_episode_api(episode_id):
    try:
        def download_in_background():
            with app.app_context():
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

@app.route('/api/config')
def get_config():
    return jsonify({
        'base_url': config.BASE_URL,
        'download_on_demand': config.DOWNLOAD_ON_DEMAND,
        'motd': os.getenv('MOTD', 'Podcast Proxy')
    })

@app.route('/api/cleanup', methods=['POST'])
@admin_required
def cleanup_database():
    try:
        from models import Episode
        feeds = podcast_db.get_feeds()
        total_checked = 0
        total_marked_missing = 0
        
        for feed in feeds:
            episodes = podcast_db.get_episodes(feed['id'])
            
            for episode in episodes:
                if episode['downloaded'] and episode['local_path']:
                    total_checked += 1
                    
                    if not os.path.exists(episode['local_path']):
                        ep = db.session.get(Episode, episode['id'])
                        if ep:
                            ep.downloaded = 0
                            ep.local_path = None
                            ep.file_size = None
                        total_marked_missing += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'checked': total_checked,
            'cleaned': total_marked_missing
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/feed/<int:feed_id>/rss.xml', methods=['GET'])
def get_rss_feed(feed_id):
    # Legacy endpoint - redirect to token-based access
    return jsonify({'error': 'This endpoint requires authentication. Use /feed/<token>/rss.xml instead'}), 401

@app.route('/feed/<token>/rss.xml', methods=['GET'])
def get_rss_feed_with_token(token):
    try:
        # Find user by access token
        user = User.query.filter_by(access_token=token).first()
        if not user:
            return jsonify({'error': 'Invalid access token'}), 401
        
        # Extract feed_id from query parameter
        feed_id = request.args.get('feed_id', type=int)
        if not feed_id:
            return jsonify({'error': 'feed_id parameter required'}), 400
        
        xml = rss_generator.generate_feed(feed_id)
        return Response(xml, mimetype='application/xml; charset=utf-8')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/episode/<int:episode_id>/download', methods=['GET'])
def serve_episode(episode_id):
    try:
        episode = podcast_db.get_episode(episode_id)
        if not episode:
            return jsonify({'error': 'Episode not found'}), 404
        
        if episode['downloaded'] and episode['local_path'] and os.path.exists(episode['local_path']):
            return send_file(episode['local_path'], as_attachment=False)
        
        # If DOWNLOAD_ON_DEMAND is enabled and episode is not cached, trigger background download
        if config.DOWNLOAD_ON_DEMAND and episode['download_status'] != 'in_progress':
            def download_in_background():
                with app.app_context():
                    try:
                        downloader.download_episode(episode_id)
                    except Exception as e:
                        print(f"Background download error for episode {episode_id}: {e}")
            
            thread = threading.Thread(target=download_in_background, daemon=True)
            thread.start()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; ferorss/1.0)'
        }
        response = requests.get(episode['original_url'], stream=True, verify=False, headers=headers)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', 'audio/mpeg')
        content_length = int(response.headers.get('Content-Length', 0))
        
        ct_valid, ct_msg = audio_validator.validate_content_type(content_type)
        if not ct_valid:
            return jsonify({'error': f'Invalid content type: {ct_msg}'}), 400
        
        if content_length > 0:
            size_valid, size_msg = audio_validator.validate_file_size(content_length)
            if not size_valid:
                return jsonify({'error': f'Invalid file size: {size_msg}'}), 400
        
        def generate():
            first_chunk = True
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    if first_chunk:
                        magic_valid, magic_msg = audio_validator.validate_magic_bytes(chunk)
                        if not magic_valid:
                            print(f"Warning: Audio validation failed during stream: {magic_msg}")
                        first_chunk = False
                    yield chunk
        
        return Response(generate(), mimetype='audio/mpeg', headers={
            'Content-Type': content_type,
            'Content-Length': response.headers.get('Content-Length', ''),
            'Accept-Ranges': 'bytes'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        login_user(user, remember=True)
        return jsonify(user.to_dict()), 200
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    invitation_token = data.get('invitation_token')
    
    if not username or not password or not invitation_token:
        return jsonify({'error': 'Username, password, and invitation token required'}), 400
    
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    invitation = InvitationLink.query.filter_by(token=invitation_token, used=False).first()
    if not invitation:
        return jsonify({'error': 'Invalid or already used invitation token'}), 400
    
    # Create user with role from invitation and set invited_by
    user = User(
        username=username,
        role=invitation.role,
        invited_by=invitation.created_by
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()  # Get user.id before committing
    
    invitation.used = True
    invitation.used_by = user.id
    invitation.used_at = int(time.time())
    
    db.session.commit()
    
    login_user(user, remember=True)
    return jsonify(user.to_dict()), 201

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    return jsonify(current_user.to_dict()), 200

@app.route('/api/invitations', methods=['POST'])
@admin_required
def create_invitation():
    data = request.json or {}
    requested_role = data.get('role', UserRole.USER)
    
    # Define role hierarchy
    role_hierarchy = {
        UserRole.USER: 0,
        UserRole.POWERUSER: 1,
        UserRole.ADMIN: 2
    }
    
    # Validate requested role
    if requested_role not in role_hierarchy:
        return jsonify({'error': 'Invalid role'}), 400
    
    # Check if creator can assign this role (can only assign equal or lower)
    creator_level = role_hierarchy.get(current_user.role, 0)
    requested_level = role_hierarchy.get(requested_role, 0)
    
    if requested_level > creator_level:
        return jsonify({'error': 'Cannot create invitation for role higher than your own'}), 403
    
    token = InvitationLink.generate_token()
    invitation = InvitationLink(
        token=token,
        role=requested_role,
        created_by=current_user.id
    )
    db.session.add(invitation)
    db.session.commit()
    
    return jsonify(invitation.to_dict()), 201

@app.route('/api/invitations', methods=['GET'])
@admin_required
def get_invitations():
    invitations = InvitationLink.query.all()
    return jsonify([inv.to_dict() for inv in invitations]), 200

def background_sync():
    while True:
        time.sleep(config.SYNC_INTERVAL)
        print("Running background sync...")
        with app.app_context():
            try:
                rss_sync.sync_all_feeds()
            except Exception as e:
                print(f"Background sync error: {e}")

if __name__ == '__main__':
    with app.app_context():
        run_initialization()
        resume_interrupted_downloads(podcast_db, downloader, app)
    
    file_observer = start_file_watcher(podcast_db)
    
    sync_thread = threading.Thread(target=background_sync, daemon=True)
    sync_thread.start()
    
    print(f"Starting Podcast RSS Proxy on port {config.PORT}")
    print(f"Base URL: {config.BASE_URL}")
    app.run(host='0.0.0.0', port=config.PORT, debug=True)
