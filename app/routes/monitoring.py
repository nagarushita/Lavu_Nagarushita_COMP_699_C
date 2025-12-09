from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.network_interface import NetworkInterface
from app.models.capture_session import CaptureSession
from app.services.capture_service import CaptureService, InterfaceManager
from app.services.interface_discovery import InterfaceDiscoveryService

monitoring_bp = Blueprint('monitoring', __name__, url_prefix='/monitoring')
capture_service = CaptureService()
interface_manager = InterfaceManager()
interface_discovery = InterfaceDiscoveryService()

@monitoring_bp.route('/')
@login_required
def index():
    interfaces = NetworkInterface.query.all()
    # Get real stats for each interface
    interface_stats = {}
    for iface in interfaces:
        stats = interface_manager.get_interface_stats(iface.id)
        interface_stats[iface.id] = stats if stats else {
            'bandwidth_mbps': 0,
            'bandwidth_percent': 0,
            'packet_rate': 0,
            'connections': 0
        }
    return render_template('monitoring/interfaces.html', 
                         interfaces=interfaces, 
                         interface_stats=interface_stats)

@monitoring_bp.route('/interfaces')
@login_required
def interfaces():
    interfaces = NetworkInterface.query.all()
    # Get real stats for each interface
    interface_stats = {}
    for iface in interfaces:
        stats = interface_manager.get_interface_stats(iface.id)
        interface_stats[iface.id] = stats if stats else {
            'bandwidth_mbps': 0,
            'bandwidth_percent': 0,
            'packet_rate': 0,
            'connections': 0
        }
    return render_template('monitoring/interfaces.html', 
                         interfaces=interfaces, 
                         interface_stats=interface_stats)

@monitoring_bp.route('/interfaces/<int:id>')
@login_required
def interface_detail(id):
    interface = NetworkInterface.query.get_or_404(id)
    stats = interface_manager.get_interface_stats(id)
    return render_template('monitoring/interface_detail.html', interface=interface, stats=stats)

@monitoring_bp.route('/interfaces/<int:id>/configure', methods=['POST'])
@login_required
def configure_interface(id):
    interface = NetworkInterface.query.get_or_404(id)
    settings = {
        'bandwidth_limit_mbps': request.form.get('bandwidth_limit_mbps', type=int),
        'filter_ip': request.form.get('filter_ip'),
        'filter_port': request.form.get('filter_port', type=int),
        'filter_protocol': request.form.get('filter_protocol')
    }
    interface_manager.configure_interface(id, settings)
    return jsonify({'success': True})

@monitoring_bp.route('/interfaces/<int:id>/enable', methods=['POST'])
@login_required
def enable_interface(id):
    interface = NetworkInterface.query.get_or_404(id)
    interface.is_active = True
    db.session.commit()
    return jsonify({'success': True})

@monitoring_bp.route('/interfaces/<int:id>/disable', methods=['POST'])
@login_required
def disable_interface(id):
    interface = NetworkInterface.query.get_or_404(id)
    interface.is_active = False
    db.session.commit()
    return jsonify({'success': True})

@monitoring_bp.route('/interfaces/<int:id>/stats')
@login_required
def interface_stats(id):
    stats = interface_manager.get_interface_stats(id)
    return jsonify(stats)

@monitoring_bp.route('/interfaces/discover', methods=['POST'])
@login_required
def discover_interfaces():
    """Discover and sync network interfaces from the system"""
    try:
        result = interface_discovery.sync_interfaces_to_db()
        flash(f"Interface discovery complete: {result['added']} added, {result['updated']} updated, {result['deactivated']} deactivated", 'success')
        return jsonify({'success': True, **result})
    except Exception as e:
        print(f"Error discovering interfaces: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

@monitoring_bp.route('/interfaces/refresh', methods=['GET'])
@login_required
def refresh_interfaces():
    """Page redirect after discovering interfaces"""
    try:
        result = interface_discovery.sync_interfaces_to_db()
        flash(f"Discovered {result['total']} interfaces: {result['added']} new, {result['updated']} updated", 'success')
    except Exception as e:
        flash(f"Error discovering interfaces: {str(e)}", 'danger')
    return redirect(url_for('monitoring.interfaces'))

@monitoring_bp.route('/live/<int:interface_id>')
@login_required
def live(interface_id):
    interface = NetworkInterface.query.get_or_404(interface_id)
    return render_template('monitoring/live.html', interface=interface)

@monitoring_bp.route('/live/<int:interface_id>/stats')
@login_required
def live_stats(interface_id):
    stats = capture_service.get_live_stats(interface_id)
    return jsonify(stats if stats else {})

@monitoring_bp.route('/capture/start', methods=['POST'])
@login_required
def start_capture():
    try:
        data = request.get_json()
        interface_id = data.get('interface_id')
        session_name = data.get('session_name', f'Capture {interface_id}')
        
        print(f"Starting capture for interface {interface_id}, session: {session_name}")
        
        filters = {
            'ip': data.get('filter_ip'),
            'port': data.get('filter_port'),
            'protocol': data.get('filter_protocol')
        }
        
        result = capture_service.start_capture(interface_id, filters, current_user.id, session_name)
        
        print(f"Capture start result: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"Error starting capture: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)})
    return jsonify(result)

@monitoring_bp.route('/capture/<int:id>/stop', methods=['POST'])
@login_required
def stop_capture(id):
    result = capture_service.stop_capture(id)
    return jsonify(result)

@monitoring_bp.route('/capture/<int:id>/pause', methods=['POST'])
@login_required
def pause_capture(id):
    result = capture_service.pause_capture(id)
    return jsonify(result)

@monitoring_bp.route('/capture/<int:id>/resume', methods=['POST'])
@login_required
def resume_capture(id):
    result = capture_service.resume_capture(id)
    return jsonify(result)

@monitoring_bp.route('/capture/sessions')
@login_required
def sessions():
    sessions = CaptureSession.query.order_by(CaptureSession.start_time.desc()).all()
    return render_template('monitoring/sessions.html', sessions=sessions)

@monitoring_bp.route('/capture/<int:id>')
@login_required
def session_detail(id):
    session = CaptureSession.query.get_or_404(id)
    return render_template('monitoring/session_detail.html', session=session)

@monitoring_bp.route('/capture/<int:id>/packets')
@login_required
def session_packets(id):
    limit = request.args.get('limit', 100, type=int)
    packets = capture_service.get_packet_stream(id, limit)
    return jsonify(packets)
