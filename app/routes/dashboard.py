from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.dashboard import Dashboard, Widget
from app.services.dashboard_service import DashboardService

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')
dashboard_service = DashboardService()

@dashboard_bp.route('/')
@login_required
def index():
    default_dashboard = Dashboard.query.filter_by(user_id=current_user.id, is_default=True).first()
    if not default_dashboard:
        default_dashboard = Dashboard.query.filter_by(user_id=current_user.id).first()
    if default_dashboard:
        return view(default_dashboard.id)
    return render_template('dashboard/view.html', dashboard=None)

@dashboard_bp.route('/<int:id>')
@login_required
def view(id):
    dashboard = Dashboard.query.get_or_404(id)
    if dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    return render_template('dashboard/view.html', dashboard=dashboard)

@dashboard_bp.route('/create', methods=['POST'])
@login_required
def create():
    data = request.get_json()
    name = data.get('name', 'New Dashboard')
    dashboard = dashboard_service.create_dashboard(name, current_user.id)
    return jsonify({'success': True, 'id': dashboard.id})

@dashboard_bp.route('/<int:id>', methods=['PUT'])
@login_required
def update(id):
    dashboard = Dashboard.query.get_or_404(id)
    if dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    dashboard.name = data.get('name', dashboard.name)
    db.session.commit()
    return jsonify({'success': True})

@dashboard_bp.route('/<int:id>', methods=['DELETE'])
@login_required
def delete(id):
    dashboard = Dashboard.query.get_or_404(id)
    if dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(dashboard)
    db.session.commit()
    return jsonify({'success': True})

@dashboard_bp.route('/<int:id>/widget', methods=['POST'])
@login_required
def add_widget(id):
    dashboard = Dashboard.query.get_or_404(id)
    if dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    widget = dashboard_service.add_widget(id, data)
    return jsonify({'success': True, 'id': widget.id})

@dashboard_bp.route('/<int:id>/widget/<int:wid>', methods=['PUT'])
@login_required
def update_widget(id, wid):
    widget = Widget.query.get_or_404(wid)
    if widget.dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    widget.position_x = data.get('position_x', widget.position_x)
    widget.position_y = data.get('position_y', widget.position_y)
    widget.width = data.get('width', widget.width)
    widget.height = data.get('height', widget.height)
    db.session.commit()
    return jsonify({'success': True})

@dashboard_bp.route('/<int:id>/widget/<int:wid>', methods=['DELETE'])
@login_required
def delete_widget(id, wid):
    widget = Widget.query.get_or_404(wid)
    if widget.dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    dashboard_service.remove_widget(wid)
    return jsonify({'success': True})

@dashboard_bp.route('/<int:id>/layout', methods=['PUT'])
@login_required
def update_layout(id):
    dashboard = Dashboard.query.get_or_404(id)
    if dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    dashboard_service.update_layout(id, data.get('config'))
    return jsonify({'success': True})

@dashboard_bp.route('/widget/<int:wid>/data')
@login_required
def widget_data(wid):
    widget = Widget.query.get_or_404(wid)
    if widget.dashboard.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    time_range = request.args.get('time_range', '24h')
    data = dashboard_service.get_widget_data(wid, time_range)
    return jsonify(data)

@dashboard_bp.route('/templates')
@login_required
def templates():
    return jsonify({
        'templates': [
            {'id': 'network_overview', 'name': 'Network Overview'},
            {'id': 'security_monitoring', 'name': 'Security Monitoring'},
            {'id': 'performance', 'name': 'Performance Dashboard'}
        ]
    })
