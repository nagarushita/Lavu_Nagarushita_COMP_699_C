import os
import shutil
import psutil
from datetime import datetime, timedelta
from app import db
from app.models.user import User
from app.models.packet import Packet
from app.models.capture_session import CaptureSession

class SystemService:
    
    def get_system_metrics(self):
        """Get system resource metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database size
        db_path = 'instance/network_monitor.db'
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        
        # Active sessions count
        active_sessions = CaptureSession.query.filter_by(status='running').count()
        
        # Packet rate (packets in last minute)
        one_min_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_packets = Packet.query.filter(Packet.timestamp >= one_min_ago).count()
        packet_rate = recent_packets / 60 if recent_packets > 0 else 0
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': memory.used / (1024 * 1024),
            'memory_total_mb': memory.total / (1024 * 1024),
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024 * 1024 * 1024),
            'disk_total_gb': disk.total / (1024 * 1024 * 1024),
            'db_size_mb': db_size / (1024 * 1024),
            'active_sessions': active_sessions,
            'packet_rate': round(packet_rate, 2)
        }
    
    def configure_retention(self, days):
        """Configure data retention period"""
        if days < 30 or days > 730:
            return {'success': False, 'message': 'Retention must be between 30 and 730 days'}
        
        return {'success': True, 'retention_days': days}
    
    def run_cleanup(self):
        """Run database cleanup"""
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        # Delete old packets
        old_packets = Packet.query.filter(Packet.timestamp < cutoff_date).delete()
        
        # Update sessions without packets
        orphan_sessions = CaptureSession.query.filter(
            CaptureSession.end_time < cutoff_date,
            CaptureSession.status == 'completed'
        ).update({'status': 'archived'})
        
        db.session.commit()
        
        # Vacuum database (SQLite specific)
        db.session.execute(db.text('VACUUM'))
        
        return {
            'success': True,
            'packets_deleted': old_packets,
            'sessions_archived': orphan_sessions,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def backup_database(self):
        """Create database backup"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_dir = 'backups'
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        db_path = 'instance/network_monitor.db'
        backup_path = os.path.join(backup_dir, f'backup_{timestamp}.db')
        
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            
            # Compress backup
            shutil.make_archive(backup_path, 'gztar', backup_dir, f'backup_{timestamp}.db')
            os.remove(backup_path)
            
            return {
                'success': True,
                'filename': f'backup_{timestamp}.db.tar.gz',
                'size_mb': os.path.getsize(f'{backup_path}.tar.gz') / (1024 * 1024)
            }
        
        return {'success': False, 'message': 'Database file not found'}
    
    def restore_database(self, backup_file):
        """Restore database from backup"""
        if not backup_file:
            return {'success': False, 'message': 'No backup file provided'}
        
        import shutil
        import tarfile
        
        try:
            with tarfile.open(backup_file, 'r:gz') as tar:
                tar.extractall(path='temp_restore')
            
            db_path = 'instance/network_monitor.db'
            restored_db = 'temp_restore/backup.db'
            
            if os.path.exists(restored_db):
                shutil.copy2(restored_db, db_path)
                shutil.rmtree('temp_restore')
                
                return {
                    'success': True,
                    'message': 'Database restored successfully',
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            return {'success': False, 'message': f'Restore failed: {str(e)}'}
        
        return {
            'success': True,
            'message': 'Database restore initiated',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_user_list(self):
        """Get list of all users"""
        users = User.query.all()
        
        return [
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'is_active': user.is_active,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat()
            }
            for user in users
        ]
    
    def manage_user(self, user_id, action, params=None):
        """Manage user actions"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        if action == 'activate':
            user.is_active = True
        elif action == 'deactivate':
            user.is_active = False
        elif action == 'change_role':
            if params and 'role' in params:
                user.role = params['role']
        elif action == 'reset_password':
            if params and 'password' in params:
                user.set_password(params['password'])
                user.failed_login_attempts = 0
        
        db.session.commit()
        
        return {'success': True}
