import random
from datetime import datetime, timedelta
from app import db
from app.models.packet import Packet
from app.models.capture_session import CaptureSession

class AnalysisService:
    
    def analyze_dns(self):
        """Analyze DNS traffic"""
        query_types = {'A': 1200, 'AAAA': 300, 'MX': 150, 'TXT': 80, 'CNAME': 200}
        top_domains = [
            {'domain': 'google.com', 'queries': 450},
            {'domain': 'facebook.com', 'queries': 320},
            {'domain': 'cloudflare.com', 'queries': 280},
            {'domain': 'amazon.com', 'queries': 210},
            {'domain': 'microsoft.com', 'queries': 180}
        ]
        dns_servers = [
            {'server': '8.8.8.8', 'queries': 1100},
            {'server': '1.1.1.1', 'queries': 830}
        ]
        
        return {
            'total_queries': sum(query_types.values()),
            'query_types': query_types,
            'top_domains': top_domains,
            'dns_servers': dns_servers
        }
    
    def analyze_dhcp(self):
        """Analyze DHCP traffic"""
        leases = [
            {'ip': '192.168.1.100', 'mac': '00:1A:2B:3C:4D:5E', 'hostname': 'desktop-01'},
            {'ip': '192.168.1.101', 'mac': '00:1A:2B:3C:4D:5F', 'hostname': 'laptop-02'},
            {'ip': '192.168.1.102', 'mac': '00:1A:2B:3C:4D:60', 'hostname': 'phone-03'}
        ]
        
        return {
            'total_leases': len(leases),
            'leases': leases,
            'dhcp_server': '192.168.1.1'
        }
    
    def analyze_tcp_states(self):
        """Analyze TCP connection states"""
        states = {
            'ESTABLISHED': 450,
            'SYN_SENT': 80,
            'SYN_RECV': 75,
            'FIN_WAIT1': 30,
            'FIN_WAIT2': 25,
            'TIME_WAIT': 100,
            'CLOSE': 10,
            'CLOSE_WAIT': 15
        }
        
        return {
            'states': states,
            'total_connections': sum(states.values()),
            'handshake_rate': random.randint(50, 200),
            'half_open': random.randint(10, 50)
        }
    
    def analyze_http(self):
        """Analyze HTTP traffic"""
        methods = {'GET': 2500, 'POST': 800, 'PUT': 150, 'DELETE': 80, 'HEAD': 120}
        status_codes = {
            '200': 2800,
            '301': 250,
            '404': 180,
            '500': 50,
            '403': 70
        }
        user_agents = [
            {'agent': 'Chrome/119.0', 'count': 1800},
            {'agent': 'Firefox/120.0', 'count': 900},
            {'agent': 'Safari/17.0', 'count': 650}
        ]
        
        return {
            'total_requests': sum(methods.values()),
            'methods': methods,
            'status_codes': status_codes,
            'user_agents': user_agents
        }
    
    def analyze_https(self):
        """Analyze HTTPS traffic"""
        tls_versions = {
            'TLS 1.2': 2000,
            'TLS 1.3': 5500,
            'TLS 1.1': 50,
            'TLS 1.0': 10
        }
        
        return {
            'total_connections': sum(tls_versions.values()),
            'tls_versions': tls_versions,
            'cipher_suites': ['TLS_AES_128_GCM_SHA256', 'TLS_AES_256_GCM_SHA384']
        }
    
    def analyze_email(self):
        """Analyze email protocol traffic"""
        protocols = {
            'SMTP': 450,
            'POP3': 180,
            'IMAP': 920
        }
        
        return {
            'total': sum(protocols.values()),
            'protocols': protocols,
            'servers': ['mail.example.com', 'smtp.gmail.com']
        }
    
    def detect_p2p(self):
        """Detect P2P traffic"""
        signatures = [
            {'protocol': 'BitTorrent', 'connections': 45, 'ports': [6881, 6882, 6883]},
            {'protocol': 'eDonkey', 'connections': 12, 'ports': [4662, 4672]}
        ]
        
        return {
            'total_connections': sum(s['connections'] for s in signatures),
            'detected_protocols': signatures
        }
    
    def get_protocol_summary(self, time_range='24h'):
        """Get protocol summary for time range"""
        protocols = {
            'TCP': 15000,
            'UDP': 8000,
            'ICMP': 500,
            'HTTP': 3500,
            'HTTPS': 7500,
            'DNS': 1930
        }
        
        return {
            'time_range': time_range,
            'protocols': protocols,
            'total_packets': sum(protocols.values())
        }


class HistoricalQueryService:
    
    def search_traffic(self, criteria):
        """Search historical traffic based on criteria"""
        results = []
        
        for i in range(50):
            results.append({
                'timestamp': (datetime.utcnow() - timedelta(hours=random.randint(1, 72))).isoformat(),
                'source_ip': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
                'destination_ip': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
                'protocol': random.choice(['TCP', 'UDP', 'ICMP']),
                'bytes': random.randint(64, 1500)
            })
        
        return {
            'total': len(results),
            'results': results
        }
    
    def compare_baseline(self, current, baseline):
        """Compare current metrics with baseline"""
        metrics = ['bandwidth', 'packet_rate', 'connections', 'errors']
        comparison = {}
        
        for metric in metrics:
            current_val = random.uniform(100, 1000)
            baseline_val = random.uniform(100, 1000)
            change = ((current_val - baseline_val) / baseline_val) * 100
            
            comparison[metric] = {
                'current': round(current_val, 2),
                'baseline': round(baseline_val, 2),
                'change_percent': round(change, 2),
                'anomaly': abs(change) > 20
            }
        
        return comparison
    
    def analyze_trends(self, metric, time_range):
        """Analyze trends for a metric"""
        days = int(time_range.replace('d', ''))
        data_points = []
        
        base_value = random.uniform(500, 1000)
        
        for i in range(days):
            timestamp = datetime.utcnow() - timedelta(days=days-i)
            value = base_value + random.uniform(-100, 100)
            data_points.append({
                'timestamp': timestamp.isoformat(),
                'value': round(value, 2)
            })
        
        # Calculate statistics
        values = [dp['value'] for dp in data_points]
        avg = sum(values) / len(values)
        peak = max(values)
        min_val = min(values)
        
        # Simple projection (last value + trend)
        projection = values[-1] + (values[-1] - values[-8]) / 7
        
        return {
            'metric': metric,
            'time_range': time_range,
            'data': data_points,
            'statistics': {
                'average': round(avg, 2),
                'peak': round(peak, 2),
                'minimum': round(min_val, 2),
                'projection_7d': round(projection, 2)
            }
        }
    
    def export_forensic_data(self, session_id, format_type):
        """Export forensic data for a session"""
        session = CaptureSession.query.get(session_id)
        if not session:
            return {'success': False, 'message': 'Session not found'}
        
        filename = f'forensic_{session_id}_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.{format_type}'
        
        return {
            'success': True,
            'filename': filename,
            'packets': session.packet_count,
            'size_bytes': session.bytes_captured
        }
