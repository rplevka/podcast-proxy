from functools import wraps
from flask import jsonify
from flask_login import current_user
from models import UserRole

def role_required(*roles):
    """Decorator to require specific roles for an endpoint."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            
            if current_user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role."""
    return role_required(UserRole.ADMIN)(f)

def poweruser_required(f):
    """Decorator to require poweruser or admin role."""
    return role_required(UserRole.POWERUSER, UserRole.ADMIN)(f)

def can_modify_feed(user, feed):
    """Check if user can modify a feed."""
    if not user:
        return False
    if user.role == UserRole.ADMIN:
        return True
    if user.role == UserRole.POWERUSER and feed.owner_id == user.id:
        return True
    return False
