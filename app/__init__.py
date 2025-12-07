from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, async_mode=app.config['SOCKETIO_ASYNC_MODE'])
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.monitoring import monitoring_bp
    from app.routes.alerts import alerts_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.reports import reports_bp
    from app.routes.analysis import analysis_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(admin_bp)
    
    # Add context processor for global template variables
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        if current_user.is_authenticated:
            from app.models.alert import Alert
            active_alert_count = Alert.query.filter_by(status='active').count()
            return {'active_alert_count': active_alert_count}
        return {'active_alert_count': 0}
    
    # Add root route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))
    
    # Create database tables and initialize default data
    with app.app_context():
        db.create_all()
        cleanup_orphaned_sessions()
        initialize_default_data()
    
    return app

def cleanup_orphaned_sessions():
    """Clean up sessions that were marked as running but have no active thread"""
    from app.models.capture_session import CaptureSession
    from datetime import datetime, timedelta
    
    # Find sessions that have been "running" for more than 1 hour without updates
    # or sessions that are running but created before the app started
    orphaned = CaptureSession.query.filter(
        CaptureSession.status.in_(['running', 'paused']),
        CaptureSession.packet_count == 0
    ).all()
    
    for session in orphaned:
        # Check if session was created more than 5 minutes ago and still has 0 packets
        if session.start_time < datetime.utcnow() - timedelta(minutes=5):
            session.status = 'failed'
            session.end_time = datetime.utcnow()
            if session.interface:
                session.interface.is_monitoring = False
    
    db.session.commit()
    
    if orphaned:
        print(f"Cleaned up {len(orphaned)} orphaned capture sessions")

def initialize_default_data():
    from app.models.user import User
    from app.models.network_interface import NetworkInterface
    from app.models.dashboard import Dashboard, Widget
    from app.models.alert import AlertRule, Alert
    from app.models.capture_session import CaptureSession
    from app.models.packet import Packet
    from app.models.audit_log import AuditLog
    from datetime import datetime, timedelta
    import random
    
    # Create admin user if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@localhost', role='super_admin', is_active=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()
    
    # Create sample users
    if User.query.count() <= 1:
        sample_users = [
            User(username='analyst1', email='analyst1@localhost', role='analyst', is_active=True),
            User(username='analyst2', email='analyst2@localhost', role='analyst', is_active=True),
            User(username='viewer1', email='viewer1@localhost', role='viewer', is_active=True),
        ]
        for user in sample_users:
            user.set_password('password123')
            db.session.add(user)
        db.session.flush()
    
    # Create default network interfaces if not exist
    if NetworkInterface.query.count() == 0:
        interfaces = [
            NetworkInterface(name='eth0', display_name='Ethernet 0', ip_address='192.168.1.10', 
                           mac_address='00:1A:2B:3C:4D:5E', is_active=True, is_monitoring=True, bandwidth_limit_mbps=1000),
            NetworkInterface(name='eth1', display_name='Ethernet 1', ip_address='10.0.0.10', 
                           mac_address='00:1A:2B:3C:4D:5F', is_active=True, is_monitoring=False, bandwidth_limit_mbps=1000),
            NetworkInterface(name='wlan0', display_name='Wireless 0', ip_address='192.168.1.20', 
                           mac_address='00:1A:2B:3C:4D:60', is_active=True, is_monitoring=True, bandwidth_limit_mbps=100),
            NetworkInterface(name='docker0', display_name='Docker Bridge', ip_address='172.17.0.1', 
                           mac_address='02:42:AC:11:00:00', is_active=True, is_monitoring=False, bandwidth_limit_mbps=10000),
            NetworkInterface(name='lo', display_name='Loopback', ip_address='127.0.0.1', 
                           mac_address='00:00:00:00:00:00', is_active=True, is_monitoring=False, bandwidth_limit_mbps=None)
        ]
        for iface in interfaces:
            db.session.add(iface)
        db.session.flush()
    
    # Create alert rules
    if AlertRule.query.count() == 0:
        alert_rules = [
            AlertRule(name='High Bandwidth Usage', description='Alert when bandwidth exceeds 800 Mbps',
                     rule_type='bandwidth', condition='exceeds', threshold_value=800, threshold_unit='Mbps',
                     severity='critical', is_active=True, notify_email=True, escalation_minutes=5,
                     created_by=admin.id),
            AlertRule(name='Suspicious Port Scan', description='Detect potential port scanning activity',
                     rule_type='connection', condition='exceeds', threshold_value=100, threshold_unit='connections/min',
                     severity='high', is_active=True, notify_email=True, escalation_minutes=10,
                     created_by=admin.id),
            AlertRule(name='Unusual Protocol Detected', description='Alert on unexpected protocol usage',
                     rule_type='protocol', condition='detected', threshold_value=1, threshold_unit='occurrence',
                     severity='medium', is_active=True, notify_email=False, escalation_minutes=15,
                     created_by=admin.id),
            AlertRule(name='High Packet Rate', description='Alert when packet rate exceeds normal threshold',
                     rule_type='packet_rate', condition='exceeds', threshold_value=50000, threshold_unit='pps',
                     severity='high', is_active=True, notify_email=True, escalation_minutes=10,
                     created_by=admin.id),
            AlertRule(name='Geographic Anomaly', description='Connections from unexpected locations',
                     rule_type='geographic', condition='detected', threshold_value=1, threshold_unit='occurrence',
                     severity='medium', is_active=False, notify_email=True, escalation_minutes=20,
                     created_by=admin.id),
        ]
        for rule in alert_rules:
            db.session.add(rule)
        db.session.flush()
        
        # Create some alerts (both active and resolved)
        now = datetime.utcnow()
        alerts = [
            Alert(rule_id=alert_rules[0].id, triggered_at=now - timedelta(hours=2),
                 status='active', triggered_value=850.5, 
                 details='Bandwidth on eth0 exceeded threshold: 850.5 Mbps'),
            Alert(rule_id=alert_rules[1].id, triggered_at=now - timedelta(hours=5),
                 resolved_at=now - timedelta(hours=4, minutes=30), status='resolved',
                 triggered_value=125, acknowledged_by=admin.id,
                 details='Port scan detected from IP 192.168.1.100, 125 connections in 1 minute'),
            Alert(rule_id=alert_rules[3].id, triggered_at=now - timedelta(hours=1),
                 status='active', triggered_value=55234,
                 details='Packet rate spike detected: 55,234 pps on wlan0'),
            Alert(rule_id=alert_rules[0].id, triggered_at=now - timedelta(days=1),
                 resolved_at=now - timedelta(days=1, hours=-1), status='resolved',
                 triggered_value=820.3, acknowledged_by=admin.id,
                 details='Bandwidth on eth0 exceeded threshold: 820.3 Mbps'),
            Alert(rule_id=alert_rules[2].id, triggered_at=now - timedelta(hours=3),
                 resolved_at=now - timedelta(hours=2, minutes=45), status='resolved',
                 triggered_value=1, acknowledged_by=admin.id,
                 details='Unusual protocol detected: SCTP on interface eth1'),
        ]
        for alert in alerts:
            db.session.add(alert)
        db.session.flush()
    
    # Create capture sessions
    interfaces = NetworkInterface.query.all()
    if CaptureSession.query.count() == 0 and interfaces:
        sessions = [
            CaptureSession(session_name='Morning Traffic Analysis', interface_id=interfaces[0].id,
                          user_id=admin.id, status='completed', 
                          start_time=datetime.utcnow() - timedelta(hours=8),
                          end_time=datetime.utcnow() - timedelta(hours=6),
                          packet_count=145230, bytes_captured=892456789,
                          filter_protocol='TCP'),
            CaptureSession(session_name='Web Traffic Monitoring', interface_id=interfaces[0].id,
                          user_id=admin.id, status='completed',
                          start_time=datetime.utcnow() - timedelta(hours=4),
                          end_time=datetime.utcnow() - timedelta(hours=2),
                          packet_count=89456, bytes_captured=456234567,
                          filter_port=443),
            CaptureSession(session_name='Real-time Monitoring', interface_id=interfaces[2].id,
                          user_id=admin.id, status='running',
                          start_time=datetime.utcnow() - timedelta(minutes=45),
                          packet_count=23456, bytes_captured=123456789),
            CaptureSession(session_name='Security Audit', interface_id=interfaces[0].id,
                          user_id=admin.id, status='completed',
                          start_time=datetime.utcnow() - timedelta(days=1),
                          end_time=datetime.utcnow() - timedelta(days=1, hours=-3),
                          packet_count=234567, bytes_captured=1234567890,
                          filter_ip='192.168.1.0/24'),
        ]
        for session in sessions:
            db.session.add(session)
        db.session.flush()
        
        # Add sample packets for completed sessions
        sample_ips = ['192.168.1.100', '192.168.1.101', '10.0.0.50', '172.217.14.206', '151.101.1.140']
        protocols = ['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS', 'DNS', 'SSH']
        
        for session in sessions[:2]:  # Add packets to first 2 completed sessions
            for i in range(50):  # Add 50 sample packets per session
                src_ip = random.choice(sample_ips)
                dst_ip = random.choice(sample_ips)
                protocol = random.choice(protocols)
                packet = Packet(
                    session_id=session.id,
                    timestamp=session.start_time + timedelta(seconds=i*10),
                    source_ip=src_ip,
                    destination_ip=dst_ip,
                    source_port=random.randint(1024, 65535),
                    destination_port=random.choice([80, 443, 22, 53, 3306, 5432]),
                    protocol=protocol,
                    length=random.randint(64, 1500),
                    flags='SYN,ACK' if protocol == 'TCP' else None,
                    payload_preview=f'Sample {protocol} packet data...'
                )
                db.session.add(packet)
    
    # Create audit logs
    if AuditLog.query.count() == 0:
        now = datetime.utcnow()
        audit_logs = [
            AuditLog(user_id=admin.id, action='login', resource_type='auth',
                    details='Successful login', ip_address='127.0.0.1',
                    user_agent='Mozilla/5.0', timestamp=now - timedelta(hours=8)),
            AuditLog(user_id=admin.id, action='create_alert_rule', resource_type='alert_rule',
                    resource_id=1, details='Created alert rule: High Bandwidth Usage',
                    ip_address='127.0.0.1', user_agent='Mozilla/5.0',
                    timestamp=now - timedelta(hours=7)),
            AuditLog(user_id=admin.id, action='start_capture', resource_type='capture_session',
                    resource_id=1, details='Started capture session on eth0',
                    ip_address='127.0.0.1', user_agent='Mozilla/5.0',
                    timestamp=now - timedelta(hours=6)),
            AuditLog(user_id=admin.id, action='acknowledge_alert', resource_type='alert',
                    resource_id=2, details='Acknowledged alert',
                    ip_address='127.0.0.1', user_agent='Mozilla/5.0',
                    timestamp=now - timedelta(hours=5)),
            AuditLog(user_id=admin.id, action='export_report', resource_type='report',
                    details='Generated traffic summary report',
                    ip_address='127.0.0.1', user_agent='Mozilla/5.0',
                    timestamp=now - timedelta(hours=3)),
        ]
        for log in audit_logs:
            db.session.add(log)
    
    # Create default dashboard if not exist
    if admin and Dashboard.query.filter_by(user_id=admin.id).count() == 0:
        dashboard = Dashboard(name='Network Overview', user_id=admin.id, is_default=True, 
                            layout_config='{"columns": 3, "rowHeight": 100}')
        db.session.add(dashboard)
        db.session.flush()
        
        # Add default widgets
        widgets = [
            Widget(dashboard_id=dashboard.id, widget_type='gauge', title='Bandwidth Usage',
                  data_source='bandwidth_usage', position_x=0, position_y=0, width=1, height=2,
                  config='{"unit": "Mbps", "max": 1000}'),
            Widget(dashboard_id=dashboard.id, widget_type='line_chart', title='Packet Rate',
                  data_source='packet_rate', position_x=1, position_y=0, width=2, height=2,
                  config='{"interval": "5s"}'),
            Widget(dashboard_id=dashboard.id, widget_type='pie_chart', title='Protocol Distribution',
                  data_source='protocol_distribution', position_x=0, position_y=2, width=1, height=2,
                  config='{}'),
            Widget(dashboard_id=dashboard.id, widget_type='table', title='Top Talkers',
                  data_source='top_talkers', position_x=1, position_y=2, width=2, height=2,
                  config='{"limit": 10}')
        ]
        for widget in widgets:
            db.session.add(widget)
    
    db.session.commit()
    print("Initial data loaded successfully")

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    return User.query.get(int(user_id))
