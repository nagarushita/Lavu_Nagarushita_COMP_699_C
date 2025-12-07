from datetime import datetime, timedelta
import re
from app import db
from app.models.user import User
from app.models.audit_log import AuditLog

class AuthenticationService:
    
    def login(self, username, password, mfa_token=None):
        """Authenticate user with username, password, and optional MFA token"""
        user = User.query.filter_by(username=username).first()
        
        if not user:
            return {'success': False, 'message': 'Invalid credentials'}
        
        if user.failed_login_attempts >= 5:
            return {'success': False, 'message': 'Account locked. Contact administrator.'}
        
        if not user.check_password(password):
            user.failed_login_attempts += 1
            db.session.commit()
            return {'success': False, 'message': 'Invalid credentials'}
        
        if user.mfa_enabled:
            if not mfa_token:
                return {'success': False, 'message': 'MFA token required', 'mfa_required': True}
            if not user.verify_mfa_token(mfa_token):
                return {'success': False, 'message': 'Invalid MFA token'}
        
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        return {'success': True, 'user': user}
    
    def logout(self, user_id):
        """Log out user"""
        return {'success': True}
    
    def register_user(self, username, email, password, role='viewer'):
        """Register new user"""
        if User.query.filter_by(username=username).first():
            return {'success': False, 'message': 'Username already exists'}
        
        if User.query.filter_by(email=email).first():
            return {'success': False, 'message': 'Email already exists'}
        
        if not self._validate_password_strength(password):
            return {'success': False, 'message': 'Password does not meet requirements'}
        
        user = User(username=username, email=email, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return {'success': True, 'user_id': user.id}
    
    def reset_password(self, email):
        """Generate password reset token"""
        user = User.query.filter_by(email=email).first()
        if not user:
            return {'success': False, 'message': 'Email not found'}
        token = f'reset_{user.id}_{datetime.utcnow().timestamp()}'
        
        return {'success': True, 'token': token}
    
    def change_password(self, user_id, old_password, new_password):
        """Change user password"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        if not user.check_password(old_password):
            return {'success': False, 'message': 'Current password is incorrect'}
        
        if not self._validate_password_strength(new_password):
            return {'success': False, 'message': 'Password does not meet requirements'}
        
        user.set_password(new_password)
        db.session.commit()
        
        return {'success': True}
    
    def setup_mfa(self, user_id):
        """Setup MFA for user"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        secret = user.generate_mfa_secret()
        uri = user.get_mfa_uri()
        db.session.commit()
        
        return {'success': True, 'secret': secret, 'uri': uri}
    
    def verify_mfa_setup(self, user_id, token):
        """Verify MFA setup with token"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        if user.verify_mfa_token(token):
            user.mfa_enabled = True
            db.session.commit()
            return {'success': True}
        
        return {'success': False, 'message': 'Invalid token'}
    
    def disable_mfa(self, user_id, password):
        """Disable MFA for user"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        if not user.check_password(password):
            return {'success': False, 'message': 'Invalid password'}
        
        user.mfa_enabled = False
        user.mfa_secret = None
        db.session.commit()
        
        return {'success': True}
    
    def _validate_password_strength(self, password):
        """Validate password meets strength requirements"""
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'[0-9]', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True
