import secrets
import string
from models import db, User, UserRole, Feed
from datetime import datetime, UTC

def generate_random_password(length=16):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def init_superadmin():
    """Initialize superadmin user if it doesn't exist."""
    superadmin = User.query.filter_by(username='superadmin').first()
    
    if not superadmin:
        password = generate_random_password()
        superadmin = User(
            username='superadmin',
            role=UserRole.ADMIN
        )
        superadmin.set_password(password)
        db.session.add(superadmin)
        db.session.commit()
        
        print("=" * 60)
        print("SUPERADMIN ACCOUNT CREATED")
        print("=" * 60)
        print(f"Username: superadmin")
        print(f"Password: {password}")
        print("=" * 60)
        print("IMPORTANT: Save this password! It will not be shown again.")
        print("=" * 60)
        
        return superadmin, password
    else:
        print("Superadmin account already exists")
        return superadmin, None

def migrate_existing_feeds_to_superadmin():
    """Assign all feeds without an owner to superadmin."""
    superadmin = User.query.filter_by(username='superadmin').first()
    
    if not superadmin:
        print("Error: Superadmin not found. Cannot migrate feeds.")
        return
    
    orphaned_feeds = Feed.query.filter_by(owner_id=None).all()
    
    if orphaned_feeds:
        print(f"Migrating {len(orphaned_feeds)} orphaned feeds to superadmin...")
        for feed in orphaned_feeds:
            feed.owner_id = superadmin.id
        db.session.commit()
        print(f"Successfully migrated {len(orphaned_feeds)} feeds to superadmin")
    else:
        print("No orphaned feeds found")

def run_initialization():
    """Run all initialization tasks."""
    superadmin, password = init_superadmin()
    migrate_existing_feeds_to_superadmin()
