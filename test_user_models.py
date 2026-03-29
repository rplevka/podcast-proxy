import pytest
from datetime import datetime, UTC
from flask import Flask
from models import db, User, InvitationLink, UserRole
from werkzeug.security import check_password_hash


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
def app_context(app):
    """Provide an application context for tests."""
    with app.app_context():
        yield


class TestUserRole:
    """Test UserRole enum constants."""
    
    def test_user_role_values(self):
        """Test that UserRole has correct values."""
        assert UserRole.USER == 'user'
        assert UserRole.POWERUSER == 'poweruser'
        assert UserRole.ADMIN == 'admin'
    
    def test_user_role_uniqueness(self):
        """Test that all UserRole values are unique."""
        values = [UserRole.USER, UserRole.POWERUSER, UserRole.ADMIN]
        assert len(values) == len(set(values))


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self, app_context):
        """Test creating a User instance."""
        user = User(username='testuser', role=UserRole.USER)
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.role == UserRole.USER
        assert user.password_hash is not None
        assert user.access_token is not None
    
    def test_user_password_hashing(self, app_context):
        """Test that passwords are properly hashed."""
        user = User(username='testuser')
        user.set_password('mypassword')
        db.session.add(user)
        db.session.commit()
        
        assert user.password_hash != 'mypassword'
        assert user.check_password('mypassword')
        assert not user.check_password('wrongpassword')
    
    def test_user_default_role(self, app_context):
        """Test that default role is USER."""
        user = User(username='testuser')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        assert user.role == UserRole.USER
    
    def test_user_access_token_auto_generated(self, app_context):
        """Test that access_token is automatically generated."""
        user = User(username='testuser')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        assert user.access_token is not None
        assert len(user.access_token) > 20
    
    def test_user_access_token_unique(self, app_context):
        """Test that access_token is unique for each user."""
        user1 = User(username='user1')
        user1.set_password('password')
        user2 = User(username='user2')
        user2.set_password('password')
        db.session.add_all([user1, user2])
        db.session.commit()
        
        assert user1.access_token != user2.access_token
    
    def test_user_regenerate_access_token(self, app_context):
        """Test regenerating access token."""
        user = User(username='testuser')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        old_token = user.access_token
        new_token = user.regenerate_access_token()
        db.session.commit()
        
        assert new_token != old_token
        assert user.access_token == new_token
    
    def test_user_created_at_auto_set(self, app_context):
        """Test that created_at is automatically set."""
        before = int(datetime.now(UTC).timestamp())
        user = User(username='testuser')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        after = int(datetime.now(UTC).timestamp())
        
        assert user.created_at is not None
        assert before <= user.created_at <= after
    
    def test_user_unique_username_constraint(self, app_context):
        """Test that username must be unique."""
        user1 = User(username='testuser')
        user1.set_password('password')
        db.session.add(user1)
        db.session.commit()
        
        user2 = User(username='testuser')
        user2.set_password('password')
        db.session.add(user2)
        
        with pytest.raises(Exception):
            db.session.commit()
    
    def test_user_to_dict(self, app_context):
        """Test User.to_dict() method."""
        user = User(username='testuser', role=UserRole.ADMIN)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        user_dict = user.to_dict()
        
        assert user_dict['id'] == user.id
        assert user_dict['username'] == 'testuser'
        assert user_dict['role'] == UserRole.ADMIN
        assert user_dict['created_at'] == user.created_at
        assert user_dict['access_token'] == user.access_token
        assert 'password_hash' not in user_dict
    
    def test_user_different_roles(self, app_context):
        """Test creating users with different roles."""
        user1 = User(username='user1', role=UserRole.USER)
        user1.set_password('password')
        user2 = User(username='user2', role=UserRole.POWERUSER)
        user2.set_password('password')
        user3 = User(username='user3', role=UserRole.ADMIN)
        user3.set_password('password')
        db.session.add_all([user1, user2, user3])
        db.session.commit()
        
        assert user1.role == UserRole.USER
        assert user2.role == UserRole.POWERUSER
        assert user3.role == UserRole.ADMIN
    
    def test_user_invited_by_relationship(self, app_context):
        """Test invited_by relationship."""
        inviter = User(username='inviter', role=UserRole.ADMIN)
        inviter.set_password('password')
        db.session.add(inviter)
        db.session.commit()
        
        invited = User(username='invited', invited_by=inviter.id)
        invited.set_password('password')
        db.session.add(invited)
        db.session.commit()
        
        assert invited.invited_by == inviter.id
        assert invited.inviter.username == 'inviter'
        assert invited in inviter.invited_users
    
    def test_user_without_inviter(self, app_context):
        """Test user created without inviter (e.g., superadmin)."""
        user = User(username='superadmin', role=UserRole.ADMIN)
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        assert user.invited_by is None
        assert user.inviter is None


class TestInvitationLinkModel:
    """Test InvitationLink model functionality."""
    
    def test_invitation_creation(self, app_context):
        """Test creating an InvitationLink instance."""
        creator = User(username='creator', role=UserRole.ADMIN)
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        invitation = InvitationLink(
            token='test-token-123',
            role=UserRole.USER,
            created_by=creator.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.id is not None
        assert invitation.token == 'test-token-123'
        assert invitation.role == UserRole.USER
        assert invitation.created_by == creator.id
        assert invitation.used is False
        assert invitation.used_by is None
    
    def test_invitation_generate_token(self):
        """Test static method to generate token."""
        token = InvitationLink.generate_token()
        
        assert token is not None
        assert len(token) > 20
        assert isinstance(token, str)
    
    def test_invitation_default_values(self, app_context):
        """Test InvitationLink default values."""
        creator = User(username='creator')
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        invitation = InvitationLink(
            token=InvitationLink.generate_token(),
            created_by=creator.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.role == UserRole.USER
        assert invitation.used is False
        assert invitation.used_by is None
        assert invitation.used_at is None
        assert invitation.created_at is not None
    
    def test_invitation_mark_as_used(self, app_context):
        """Test marking invitation as used."""
        creator = User(username='creator')
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        user = User(username='newuser')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        invitation = InvitationLink(
            token=InvitationLink.generate_token(),
            created_by=creator.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        invitation.used = True
        invitation.used_by = user.id
        invitation.used_at = int(datetime.now(UTC).timestamp())
        db.session.commit()
        
        assert invitation.used is True
        assert invitation.used_by == user.id
        assert invitation.used_at is not None
    
    def test_invitation_unique_token_constraint(self, app_context):
        """Test that token must be unique."""
        creator = User(username='creator')
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        inv1 = InvitationLink(token='same-token', created_by=creator.id)
        db.session.add(inv1)
        db.session.commit()
        
        inv2 = InvitationLink(token='same-token', created_by=creator.id)
        db.session.add(inv2)
        
        with pytest.raises(Exception):
            db.session.commit()
    
    def test_invitation_to_dict(self, app_context):
        """Test InvitationLink.to_dict() method."""
        creator = User(username='creator')
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        invitation = InvitationLink(
            token='test-token',
            role=UserRole.POWERUSER,
            created_by=creator.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        inv_dict = invitation.to_dict()
        
        assert inv_dict['id'] == invitation.id
        assert inv_dict['token'] == 'test-token'
        assert inv_dict['role'] == UserRole.POWERUSER
        assert inv_dict['created_by'] == creator.id
        assert inv_dict['used'] is False
        assert inv_dict['used_by'] is None
        assert inv_dict['created_at'] == invitation.created_at
        assert inv_dict['used_at'] is None
    
    def test_invitation_different_roles(self, app_context):
        """Test creating invitations with different roles."""
        creator = User(username='creator', role=UserRole.ADMIN)
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        inv1 = InvitationLink(token='token1', role=UserRole.USER, created_by=creator.id)
        inv2 = InvitationLink(token='token2', role=UserRole.POWERUSER, created_by=creator.id)
        inv3 = InvitationLink(token='token3', role=UserRole.ADMIN, created_by=creator.id)
        db.session.add_all([inv1, inv2, inv3])
        db.session.commit()
        
        assert inv1.role == UserRole.USER
        assert inv2.role == UserRole.POWERUSER
        assert inv3.role == UserRole.ADMIN
    
    def test_invitation_creator_relationship(self, app_context):
        """Test creator relationship."""
        creator = User(username='creator', role=UserRole.ADMIN)
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        invitation = InvitationLink(
            token=InvitationLink.generate_token(),
            created_by=creator.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.creator.username == 'creator'
        assert invitation in creator.created_invitations
    
    def test_invitation_user_relationship(self, app_context):
        """Test user relationship after invitation is used."""
        creator = User(username='creator')
        creator.set_password('password')
        db.session.add(creator)
        db.session.commit()
        
        user = User(username='newuser')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        invitation = InvitationLink(
            token=InvitationLink.generate_token(),
            created_by=creator.id,
            used=True,
            used_by=user.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.user.username == 'newuser'
        assert invitation in user.used_invitation


class TestUserInvitationWorkflow:
    """Test complete user invitation workflow."""
    
    def test_complete_invitation_flow(self, app_context):
        """Test complete flow from invitation creation to user registration."""
        # Admin creates invitation
        admin = User(username='admin', role=UserRole.ADMIN)
        admin.set_password('adminpass')
        db.session.add(admin)
        db.session.commit()
        
        invitation = InvitationLink(
            token=InvitationLink.generate_token(),
            role=UserRole.POWERUSER,
            created_by=admin.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        assert invitation.used is False
        
        # New user registers with invitation
        new_user = User(
            username='newuser',
            role=invitation.role,
            invited_by=invitation.created_by
        )
        new_user.set_password('userpass')
        db.session.add(new_user)
        db.session.flush()
        
        # Mark invitation as used
        invitation.used = True
        invitation.used_by = new_user.id
        invitation.used_at = int(datetime.now(UTC).timestamp())
        db.session.commit()
        
        # Verify the complete chain
        assert new_user.role == UserRole.POWERUSER
        assert new_user.invited_by == admin.id
        assert new_user.inviter.username == 'admin'
        assert invitation.used is True
        assert invitation.used_by == new_user.id
        assert invitation.user.username == 'newuser'
    
    def test_multiple_invitations_by_same_creator(self, app_context):
        """Test admin creating multiple invitations."""
        admin = User(username='admin', role=UserRole.ADMIN)
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()
        
        inv1 = InvitationLink(token='token1', created_by=admin.id)
        inv2 = InvitationLink(token='token2', created_by=admin.id)
        inv3 = InvitationLink(token='token3', created_by=admin.id)
        db.session.add_all([inv1, inv2, inv3])
        db.session.commit()
        
        assert len(admin.created_invitations) == 3
    
    def test_query_unused_invitations(self, app_context):
        """Test querying unused invitations."""
        admin = User(username='admin')
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()
        
        inv1 = InvitationLink(token='token1', created_by=admin.id, used=False)
        inv2 = InvitationLink(token='token2', created_by=admin.id, used=True)
        inv3 = InvitationLink(token='token3', created_by=admin.id, used=False)
        db.session.add_all([inv1, inv2, inv3])
        db.session.commit()
        
        unused = InvitationLink.query.filter_by(used=False).all()
        assert len(unused) == 2
        assert inv1 in unused
        assert inv3 in unused
    
    def test_query_invitation_by_token(self, app_context):
        """Test finding invitation by token."""
        admin = User(username='admin')
        admin.set_password('password')
        db.session.add(admin)
        db.session.commit()
        
        invitation = InvitationLink(
            token='unique-token-xyz',
            created_by=admin.id
        )
        db.session.add(invitation)
        db.session.commit()
        
        found = InvitationLink.query.filter_by(token='unique-token-xyz').first()
        assert found is not None
        assert found.id == invitation.id
