from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    is_active = db.Column(db.Boolean, default=True)
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    capture_sessions = db.relationship('CaptureSession', backref='user', lazy='dynamic')
    dashboards = db.relationship('Dashboard', backref='user', lazy='dynamic')
    alert_rules = db.relationship('AlertRule', foreign_keys='AlertRule.created_by', backref='creator', lazy='dynamic')
    acknowledged_alerts = db.relationship('Alert', foreign_keys='Alert.acknowledged_by', backref='acknowledger', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_mfa_secret(self):
        """Generate new MFA secret"""
        self.mfa_secret = pyotp.random_base32()
        return self.mfa_secret
    
    def get_mfa_uri(self):
        """Get MFA provisioning URI for QR code"""
        if not self.mfa_secret:
            self.generate_mfa_secret()
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.username,
            issuer_name='Network Monitor'
        )
    
    def verify_mfa_token(self, token):
        """Verify MFA token"""
        if not self.mfa_enabled or not self.mfa_secret:
            return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)
    
    def has_permission(self, required_role):
        """Check if user has required permission level"""
        role_hierarchy = {
            'viewer': 1,
            'analyst': 2,
            'admin': 3,
            'super_admin': 4
        }
        user_level = role_hierarchy.get(self.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        return user_level >= required_level
    
    def __repr__(self):
        return f'<User {self.username}>'
