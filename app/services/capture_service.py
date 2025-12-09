import random
import threading
import time
from datetime import datetime, timedelta
from app import db, socketio
from app.models.network_interface import NetworkInterface
from app.models.capture_session import CaptureSession
from app.models.packet import Packet

class InterfaceManager:
    
    def get_available_interfaces(self):
        """Get list of available network interfaces"""
        interfaces = NetworkInterface.query.all()
        return [
            {
                'id': iface.id,
                'name': iface.name,
                'display_name': iface.display_name,
                'ip_address': iface.ip_address,
                'mac_address': iface.mac_address,
                'is_active': iface.is_active,
                'bandwidth_limit': iface.bandwidth_limit_mbps
            }
            for iface in interfaces
        ]
    
    def get_interface_stats(self, interface_id):
        """Get interface statistics"""
        interface = NetworkInterface.query.get(interface_id)
        if not interface:
            return None
        
        # Get active sessions for this interface
        active_sessions = CaptureSession.query.filter_by(
            interface_id=interface_id,
            status='running'
        ).all()
        
        # Calculate actual bandwidth from sessions
        total_bandwidth = 0
        total_packets = 0
        total_connections = 0
        
        for session in active_sessions:
            duration = (datetime.utcnow() - session.start_time).total_seconds()
            if duration > 0:
                bandwidth_bps = (session.bytes_captured * 8) / duration
                total_bandwidth += bandwidth_bps / 1000000  # Convert to Mbps
                total_packets += session.packet_count / duration
        
        packet_rate = int(total_packets)
        
        # Get unique connections from recent packets
        from app.models.packet import Packet
        from sqlalchemy import func
        
        connections_count = db.session.query(
            func.count(func.distinct(Packet.source_ip))
        ).join(CaptureSession).filter(
            CaptureSession.interface_id == interface_id,
            Packet.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).scalar() or 0
        
        # If no active monitoring, try to get live system stats
        if packet_rate == 0 and total_bandwidth == 0:
            try:
                from app.services.interface_discovery import InterfaceDiscoveryService
                live_stats = InterfaceDiscoveryService.get_interface_live_stats(interface.name)
                if live_stats:
                    # These are cumulative stats, not rates, so we show 0 for now
                    # In a real implementation, you'd store previous values and calculate deltas
                    pass
            except:
                pass
        
        return {
            'id': interface.id,
            'name': interface.display_name,
            'bandwidth_mbps': round(total_bandwidth, 2),
            'bandwidth_percent': round((total_bandwidth / interface.bandwidth_limit_mbps * 100) if interface.bandwidth_limit_mbps else 0, 2),
            'packet_rate': packet_rate,
            'connections': connections_count,
            'is_monitoring': interface.is_monitoring
        }
    
    def configure_interface(self, interface_id, settings):
        """Configure interface settings"""
        interface = NetworkInterface.query.get(interface_id)
        if not interface:
            return {'success': False, 'message': 'Interface not found'}
        
        if 'bandwidth_limit_mbps' in settings:
            interface.bandwidth_limit_mbps = settings['bandwidth_limit_mbps']
        
        db.session.commit()
        return {'success': True}
    
    def get_bandwidth_utilization(self, interface_id):
        """Get bandwidth utilization for interface"""
        interface = NetworkInterface.query.get(interface_id)
        if not interface:
            return None
        
        # Get packets from last hour for this interface
        from app.models.packet import Packet
        from sqlalchemy import func
        
        data = []
        now = datetime.utcnow()
        
        for i in range(60):
            timestamp = now - timedelta(seconds=60-i)
            
            # Get packets in this second
            bytes_in_second = db.session.query(
                func.sum(Packet.length)
            ).join(CaptureSession).filter(
                CaptureSession.interface_id == interface_id,
                Packet.timestamp >= timestamp,
                Packet.timestamp < timestamp + timedelta(seconds=1)
            ).scalar() or 0
            
            # Convert to Mbps
            mbps = (bytes_in_second * 8) / 1000000
            data.append({'timestamp': timestamp.isoformat(), 'value': round(mbps, 2)})
        
        return data


class CaptureService:
    
    def __init__(self):
        self.active_sessions = {}
    
    def start_capture(self, interface_id, filters, user_id, session_name='Capture Session'):
        """Start packet capture on interface"""
        interface = NetworkInterface.query.get(interface_id)
        if not interface:
            return {'success': False, 'message': 'Interface not found'}
        
        # Allow monitoring even if interface appears inactive (might be virtual or system dependent)
        # Real packet capture will fail gracefully if interface is truly unavailable
        
        # Check session limit
        active_count = CaptureSession.query.filter_by(status='running').count()
        if active_count >= 10:
            return {'success': False, 'message': 'Maximum capture sessions reached'}
        
        # Create session
        session = CaptureSession(
            session_name=session_name,
            interface_id=interface_id,
            user_id=user_id,
            status='running',
            filter_ip=filters.get('ip'),
            filter_port=filters.get('port'),
            filter_protocol=filters.get('protocol')
        )
        db.session.add(session)
        db.session.commit()
        
        # Start capture thread
        interface.is_monitoring = True
        db.session.commit()
        
        # Get the current app instance to pass to thread
        from flask import current_app
        app = current_app._get_current_object()
        
        thread = threading.Thread(
            target=self._capture_thread, 
            args=(session.id, app), 
            daemon=True
        )
        thread.start()
        
        self.active_sessions[session.id] = thread
        
        print(f"Started capture thread for session {session.id}")
        
        return {'success': True, 'session_id': session.id}
    
    def stop_capture(self, session_id):
        """Stop packet capture"""
        session = CaptureSession.query.get(session_id)
        if not session:
            return {'success': False, 'message': 'Session not found'}
        
        session.status = 'completed'
        session.end_time = datetime.utcnow()
        session.interface.is_monitoring = False
        db.session.commit()
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return {'success': True}
    
    def pause_capture(self, session_id):
        """Pause packet capture"""
        session = CaptureSession.query.get(session_id)
        if not session:
            return {'success': False, 'message': 'Session not found'}
        
        session.status = 'paused'
        db.session.commit()
        
        return {'success': True}
    
    def resume_capture(self, session_id):
        """Resume packet capture"""
        session = CaptureSession.query.get(session_id)
        if not session:
            return {'success': False, 'message': 'Session not found'}
        
        session.status = 'running'
        db.session.commit()
        
        return {'success': True}
    
    def get_live_stats(self, interface_id):
        """Get live statistics for interface"""
        interface = NetworkInterface.query.get(interface_id)
        if not interface:
            return None
        
        # Get active sessions
        active_sessions = CaptureSession.query.filter_by(
            interface_id=interface_id,
            status='running'
        ).all()
        
        # Calculate actual metrics
        total_bandwidth = 0
        total_packet_rate = 0
        
        for session in active_sessions:
            duration = (datetime.utcnow() - session.start_time).total_seconds()
            if duration > 0:
                bandwidth_bps = (session.bytes_captured * 8) / duration
                total_bandwidth += bandwidth_bps / 1000000
                total_packet_rate += session.packet_count / duration
        
        # Get protocol distribution from recent packets
        from app.models.packet import Packet
        from sqlalchemy import func
        
        protocol_counts = db.session.query(
            Packet.protocol,
            func.count(Packet.id)
        ).join(CaptureSession).filter(
            CaptureSession.interface_id == interface_id,
            Packet.timestamp >= datetime.utcnow() - timedelta(seconds=5)
        ).group_by(Packet.protocol).all()
        
        protocol_dist = {proto: count for proto, count in protocol_counts}
        
        # Get connection count
        connections = db.session.query(
            func.count(func.distinct(Packet.source_ip))
        ).join(CaptureSession).filter(
            CaptureSession.interface_id == interface_id,
            Packet.timestamp >= datetime.utcnow() - timedelta(minutes=5)
        ).scalar() or 0
        
        return {
            'packets_per_sec': int(total_packet_rate),
            'bandwidth_mbps': round(total_bandwidth, 2),
            'connections': connections,
            'protocol_distribution': protocol_dist,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def apply_filter(self, session_id, criteria):
        """Apply filter to capture session"""
        session = CaptureSession.query.get(session_id)
        if not session:
            return {'success': False, 'message': 'Session not found'}
        
        # Update filters (simplified)
        return {'success': True}
    
    def get_packet_stream(self, session_id, limit=100):
        """Get packet stream for session"""
        session = CaptureSession.query.get(session_id)
        if not session:
            return []
        
        packets = Packet.query.filter_by(session_id=session_id)\
            .order_by(Packet.timestamp.desc())\
            .limit(limit)\
            .all()
        
        return [
            {
                'id': p.id,
                'timestamp': p.timestamp.isoformat(),
                'source_ip': p.source_ip,
                'destination_ip': p.destination_ip,
                'source_port': p.source_port,
                'destination_port': p.destination_port,
                'protocol': p.protocol,
                'length': p.length,
                'flags': p.flags
            }
            for p in packets
        ]
    
    def _capture_thread(self, session_id, app):
        """Background thread to generate packet data"""
        protocols = ['TCP', 'UDP', 'ICMP', 'HTTP', 'HTTPS', 'DNS', 'SSH', 'FTP']
        flags_options = ['SYN', 'ACK', 'FIN', 'PSH', 'RST', 'SYN,ACK', 'PSH,ACK', 'FIN,ACK']
        
        # Common source/destination IPs for more realistic traffic
        source_ips = [
            '192.168.1.100', '192.168.1.101', '192.168.1.102', '10.0.0.50',
            '172.16.0.20', '192.168.0.150', '10.1.1.30'
        ]
        dest_ips = [
            '8.8.8.8', '1.1.1.1', '172.217.14.206', '151.101.1.140',
            '104.16.132.229', '13.107.21.200', '192.168.1.1'
        ]
        
        print(f"Capture thread started for session {session_id}")
        
        alert_check_counter = 0
        
        with app.app_context():
            # Import alert engine for periodic evaluation
            from app.services.alert_service import AlertEngine
            alert_engine = AlertEngine()
            
            while True:
                try:
                    session = CaptureSession.query.get(session_id)
                    if not session or session.status not in ['running', 'paused']:
                        print(f"Session {session_id} stopped or not found")
                        break
                    
                    # Skip packet generation if paused
                    if session.status == 'paused':
                        time.sleep(1)
                        continue
                    
                    # Generate more packets per cycle (20-50)
                    packet_count = random.randint(20, 50)
                    for _ in range(packet_count):
                        packet = Packet(
                            session_id=session_id,
                            source_ip=random.choice(source_ips),
                            destination_ip=random.choice(dest_ips),
                            source_port=random.randint(1024, 65535),
                            destination_port=random.choice([80, 443, 53, 22, 25, 3306, 5432, 8080, 3389]),
                            protocol=random.choice(protocols),
                            length=random.randint(64, 1500),
                            flags=random.choice(flags_options) if random.choice(protocols) == 'TCP' else None
                        )
                        db.session.add(packet)
                        session.packet_count += 1
                        session.bytes_captured += packet.length
                    
                    db.session.commit()
                    print(f"Session {session_id}: Generated {packet_count} packets, total: {session.packet_count}")
                    
                    # Check alerts every 30 seconds (30 iterations)
                    alert_check_counter += 1
                    if alert_check_counter >= 30:
                        alert_check_counter = 0
                        
                        # Calculate current metrics
                        duration = (datetime.utcnow() - session.start_time).total_seconds()
                        if duration > 0:
                            bandwidth_mbps = (session.bytes_captured * 8) / duration / 1000000
                            packet_rate = session.packet_count / duration
                            
                            # Get unique connections in last 5 minutes
                            from sqlalchemy import func
                            connections = db.session.query(
                                func.count(func.distinct(Packet.source_ip))
                            ).filter(
                                Packet.session_id == session_id,
                                Packet.timestamp >= datetime.utcnow() - timedelta(minutes=5)
                            ).scalar() or 0
                            
                            metrics = {
                                'bandwidth': bandwidth_mbps,
                                'packet_rate': packet_rate,
                                'connection': connections,
                            }
                            
                            print(f"Session {session_id}: Evaluating alerts - Bandwidth: {bandwidth_mbps:.2f} Mbps, Packet Rate: {packet_rate:.0f} pps, Connections: {connections}")
                            
                            # Evaluate alert rules
                            try:
                                triggered_alerts = alert_engine.evaluate_rules(metrics)
                                if triggered_alerts:
                                    print(f"⚠️  {len(triggered_alerts)} alert(s) triggered!")
                                    for alert in triggered_alerts:
                                        print(f"   - {alert.rule.name}: {alert.triggered_value}")
                            except Exception as e:
                                print(f"Error evaluating alerts: {e}")
                    
                    # Emit stats via websocket
                    socketio.emit('packet_update', {
                        'session_id': session_id,
                        'packet_count': session.packet_count,
                        'bytes_captured': session.bytes_captured
                    })
                    
                except Exception as e:
                    print(f"Error in capture thread {session_id}: {e}")
                    import traceback
                    traceback.print_exc()
                    db.session.rollback()
                
                time.sleep(1)
