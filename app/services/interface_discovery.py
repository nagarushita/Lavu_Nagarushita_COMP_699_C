"""Network interface discovery service using scapy and psutil"""
import psutil
from scapy.arch import get_if_list, get_if_addr, get_if_hwaddr
from app import db
from app.models.network_interface import NetworkInterface


class InterfaceDiscoveryService:
    """Service to discover and manage network interfaces on the system"""
    
    @staticmethod
    def discover_interfaces():
        """
        Discover all network interfaces on the system
        Returns a list of interface dictionaries
        """
        interfaces = []
        
        # Get all interface names from scapy
        iface_names = get_if_list()
        
        # Get additional info from psutil
        psutil_interfaces = psutil.net_if_addrs()
        psutil_stats = psutil.net_if_stats()
        
        for iface_name in iface_names:
            try:
                # Get IP address using scapy
                ip_address = get_if_addr(iface_name)
                if not ip_address or ip_address == '0.0.0.0':
                    # Try to get from psutil
                    if iface_name in psutil_interfaces:
                        for addr in psutil_interfaces[iface_name]:
                            if addr.family == 2:  # AF_INET (IPv4)
                                ip_address = addr.address
                                break
                
                # Get MAC address using scapy
                try:
                    mac_address = get_if_hwaddr(iface_name)
                except:
                    # Fallback to psutil
                    mac_address = '00:00:00:00:00:00'
                    if iface_name in psutil_interfaces:
                        for addr in psutil_interfaces[iface_name]:
                            if addr.family == 17 or addr.family == 18:  # AF_LINK/AF_PACKET
                                mac_address = addr.address
                                break
                
                # Get interface status
                is_active = False
                if iface_name in psutil_stats:
                    is_active = psutil_stats[iface_name].isup
                
                # Estimate bandwidth based on interface name
                bandwidth_limit = InterfaceDiscoveryService._estimate_bandwidth(iface_name)
                
                # Create a friendly display name
                display_name = InterfaceDiscoveryService._generate_display_name(iface_name)
                
                interfaces.append({
                    'name': iface_name,
                    'display_name': display_name,
                    'ip_address': ip_address or '0.0.0.0',
                    'mac_address': mac_address or '00:00:00:00:00:00',
                    'is_active': is_active,
                    'bandwidth_limit_mbps': bandwidth_limit
                })
                
            except Exception as e:
                print(f"Error processing interface {iface_name}: {e}")
                continue
        
        return interfaces
    
    @staticmethod
    def _estimate_bandwidth(iface_name):
        """Estimate bandwidth limit based on interface name"""
        name_lower = iface_name.lower()
        
        if 'lo' in name_lower or 'loopback' in name_lower:
            return None  # Loopback has no real limit
        elif 'wlan' in name_lower or 'wi-fi' in name_lower or 'wireless' in name_lower or 'airport' in name_lower:
            return 1000  # WiFi typically 1 Gbps
        elif 'eth' in name_lower or 'en' in name_lower:
            return 1000  # Ethernet typically 1 Gbps
        elif 'docker' in name_lower or 'veth' in name_lower or 'br-' in name_lower:
            return 10000  # Virtual interfaces can be very fast
        else:
            return 1000  # Default to 1 Gbps
    
    @staticmethod
    def _generate_display_name(iface_name):
        """Generate a friendly display name for the interface"""
        name_lower = iface_name.lower()
        
        if 'lo' in name_lower:
            return 'Loopback'
        elif 'wlan' in name_lower:
            return f'Wireless ({iface_name})'
        elif 'eth' in name_lower:
            return f'Ethernet ({iface_name})'
        elif 'en' in name_lower:
            return f'Network ({iface_name})'
        elif 'docker' in name_lower:
            return f'Docker Bridge ({iface_name})'
        elif 'veth' in name_lower:
            return f'Virtual Ethernet ({iface_name})'
        elif 'br-' in name_lower or 'bridge' in name_lower:
            return f'Bridge ({iface_name})'
        elif 'tun' in name_lower or 'tap' in name_lower:
            return f'VPN/Tunnel ({iface_name})'
        else:
            return iface_name
    
    @staticmethod
    def sync_interfaces_to_db():
        """
        Discover interfaces and sync them to the database
        - Adds new interfaces
        - Updates existing interfaces
        - Marks missing interfaces as inactive
        """
        discovered = InterfaceDiscoveryService.discover_interfaces()
        discovered_names = {iface['name'] for iface in discovered}
        
        # Get existing interfaces from database
        existing_interfaces = {iface.name: iface for iface in NetworkInterface.query.all()}
        
        added_count = 0
        updated_count = 0
        
        # Add or update discovered interfaces
        for iface_data in discovered:
            if iface_data['name'] in existing_interfaces:
                # Update existing interface
                iface = existing_interfaces[iface_data['name']]
                iface.ip_address = iface_data['ip_address']
                iface.mac_address = iface_data['mac_address']
                iface.is_active = iface_data['is_active']
                if not iface.bandwidth_limit_mbps:
                    iface.bandwidth_limit_mbps = iface_data['bandwidth_limit_mbps']
                updated_count += 1
            else:
                # Add new interface
                new_iface = NetworkInterface(
                    name=iface_data['name'],
                    display_name=iface_data['display_name'],
                    ip_address=iface_data['ip_address'],
                    mac_address=iface_data['mac_address'],
                    is_active=iface_data['is_active'],
                    is_monitoring=False,
                    bandwidth_limit_mbps=iface_data['bandwidth_limit_mbps']
                )
                db.session.add(new_iface)
                added_count += 1
        
        # Mark interfaces no longer present as inactive
        deactivated_count = 0
        for name, iface in existing_interfaces.items():
            if name not in discovered_names and iface.is_active:
                iface.is_active = False
                deactivated_count += 1
        
        db.session.commit()
        
        return {
            'added': added_count,
            'updated': updated_count,
            'deactivated': deactivated_count,
            'total': len(discovered)
        }
    
    @staticmethod
    def get_interface_live_stats(iface_name):
        """Get live statistics for a specific interface using psutil"""
        try:
            # Get IO counters
            io_counters = psutil.net_io_counters(pernic=True)
            
            if iface_name not in io_counters:
                return None
            
            stats = io_counters[iface_name]
            
            return {
                'bytes_sent': stats.bytes_sent,
                'bytes_recv': stats.bytes_recv,
                'packets_sent': stats.packets_sent,
                'packets_recv': stats.packets_recv,
                'errin': stats.errin,
                'errout': stats.errout,
                'dropin': stats.dropin,
                'dropout': stats.dropout
            }
        except Exception as e:
            print(f"Error getting live stats for {iface_name}: {e}")
            return None
