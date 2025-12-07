from datetime import datetime
from app import db

class CaptureSession(db.Model):
    __tablename__ = 'capture_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), nullable=False)
    interface_id = db.Column(db.Integer, db.ForeignKey('network_interfaces.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)
    packet_count = db.Column(db.Integer, default=0)
    bytes_captured = db.Column(db.BigInteger, default=0)
    filter_ip = db.Column(db.String(45), nullable=True)
    filter_port = db.Column(db.Integer, nullable=True)
    filter_protocol = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    packets = db.relationship('Packet', backref='session', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<CaptureSession {self.session_name}>'
