from datetime import datetime
from app import db

class Packet(db.Model):
    __tablename__ = 'packets'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('capture_sessions.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    source_ip = db.Column(db.String(45), nullable=False, index=True)
    destination_ip = db.Column(db.String(45), nullable=False, index=True)
    source_port = db.Column(db.Integer, nullable=True)
    destination_port = db.Column(db.Integer, nullable=True)
    protocol = db.Column(db.String(20), nullable=False, index=True)
    length = db.Column(db.Integer, nullable=False)
    flags = db.Column(db.String(20), nullable=True)
    payload_preview = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Packet {self.source_ip}:{self.source_port} -> {self.destination_ip}:{self.destination_port}>'
