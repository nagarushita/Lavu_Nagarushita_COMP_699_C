from datetime import datetime
from app import db

class NetworkInterface(db.Model):
    __tablename__ = 'network_interfaces'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)
    mac_address = db.Column(db.String(17), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_monitoring = db.Column(db.Boolean, default=False)
    bandwidth_limit_mbps = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    capture_sessions = db.relationship('CaptureSession', backref='interface', lazy='dynamic')
    
    def __repr__(self):
        return f'<NetworkInterface {self.name}>'
