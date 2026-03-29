from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, UTC
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

db = SQLAlchemy()

class UserRole:
    USER = 'user'
    POWERUSER = 'poweruser'
    ADMIN = 'admin'

class DownloadStatus:
    NOT_DOWNLOADED = 0
    DOWNLOADED = 1
    IN_PROGRESS = 2

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER)
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    access_token = db.Column(db.String(64), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))
    created_at = db.Column(db.Integer, default=lambda: int(datetime.now(UTC).timestamp()))
    
    feeds = db.relationship('Feed', backref='owner', lazy=True)
    inviter = db.relationship('User', remote_side=[id], backref='invited_users', foreign_keys=[invited_by])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def regenerate_access_token(self):
        self.access_token = secrets.token_urlsafe(32)
        return self.access_token
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at,
            'access_token': self.access_token
        }

class InvitationLink(db.Model):
    __tablename__ = 'invitation_links'
    
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.USER)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.Integer, default=lambda: int(datetime.now(UTC).timestamp()))
    used_at = db.Column(db.Integer, nullable=True)
    
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_invitations')
    user = db.relationship('User', foreign_keys=[used_by], backref='used_invitation')
    
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)
    
    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'role': self.role,
            'created_by': self.created_by,
            'used': self.used,
            'used_by': self.used_by,
            'created_at': self.created_at,
            'used_at': self.used_at
        }

class Feed(db.Model):
    __tablename__ = 'feeds'
    
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String(500), unique=True, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    last_synced = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=True)
    currency = db.Column(db.String(3), default='USD')
    created_at = db.Column(db.Integer, default=lambda: int(datetime.now(UTC).timestamp()))
    
    episodes = db.relationship('Episode', backref='feed', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'original_url': self.original_url,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'last_synced': self.last_synced,
            'owner_id': self.owner_id,
            'owner_username': self.owner.username if self.owner else None,
            'price': float(self.price) if self.price else None,
            'currency': self.currency,
            'created_at': self.created_at
        }

class Episode(db.Model):
    __tablename__ = 'episodes'
    
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feeds.id', ondelete='CASCADE'), nullable=False)
    guid = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    pub_date = db.Column(db.String(100))
    duration = db.Column(db.String(50))
    original_url = db.Column(db.String(500))
    local_path = db.Column(db.String(500))
    file_size = db.Column(db.Integer)
    downloaded = db.Column(db.Integer, default=0)
    download_status = db.Column(db.Integer, default=0)
    created_at = db.Column(db.Integer, default=lambda: int(datetime.now(UTC).timestamp()))
    
    __table_args__ = (
        db.UniqueConstraint('feed_id', 'guid', name='uq_feed_guid'),
        db.Index('idx_episodes_feed_id', 'feed_id'),
        db.Index('idx_episodes_guid', 'guid'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'feed_id': self.feed_id,
            'guid': self.guid,
            'title': self.title,
            'description': self.description,
            'pub_date': self.pub_date,
            'duration': self.duration,
            'original_url': self.original_url,
            'local_path': self.local_path,
            'file_size': self.file_size,
            'downloaded': self.downloaded,
            'download_status': self.download_status,
            'created_at': self.created_at
        }
