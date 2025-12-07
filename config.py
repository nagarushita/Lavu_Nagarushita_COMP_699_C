import os
from datetime import timedelta

class Config:
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///network_monitor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Monitoring Settings
    MAX_CAPTURE_SESSIONS = 10
    ALERT_CHECK_INTERVAL = 5  # seconds
    BANDWIDTH_THRESHOLD_PERCENT = 80
    MAX_FILTERS_PER_SESSION = 5
    PACKET_BUFFER_SIZE = 10000
    
    # Data Retention
    MIN_RETENTION_DAYS = 30
    MAX_RETENTION_DAYS = 730
    DEFAULT_RETENTION_DAYS = 90
    
    # SocketIO
    SOCKETIO_ASYNC_MODE = 'eventlet'
    
    # Upload
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
