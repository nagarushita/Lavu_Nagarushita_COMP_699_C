from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.user import User
from app.services.system_service import SystemService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
system_service = SystemService()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('super_admin'):
            return jsonify({'error': 'Super admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    metrics = system_service.get_system_metrics()
    return render_template('admin/dashboard.html', metrics=metrics)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = system_service.get_user_list()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json()
    user = User(
        username=data['username'],
        email=data['email'],
        role=data.get('role', 'viewer'),
        is_active=data.get('is_active', True)
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'id': user.id})

@admin_bp.route('/users/<int:id>', methods=['PUT'])
@login_required
@admin_required
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    
    user.email = data.get('email', user.email)
    user.role = data.get('role', user.role)
    user.is_active = data.get('is_active', user.is_active)
    
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/users/<int:id>', methods=['DELETE'])
@login_required
@super_admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete yourself'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_user_password(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    user.set_password(data['password'])
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/system')
@login_required
@admin_required
def system():
    metrics = system_service.get_system_metrics()
    return render_template('admin/system.html', metrics=metrics)

@admin_bp.route('/system/metrics')
@login_required
@admin_required
def system_metrics():
    metrics = system_service.get_system_metrics()
    return jsonify(metrics)

@admin_bp.route('/system/retention', methods=['POST'])
@login_required
@super_admin_required
def configure_retention():
    data = request.get_json()
    days = data.get('days')
    result = system_service.configure_retention(days)
    return jsonify(result)

@admin_bp.route('/system/cleanup', methods=['POST'])
@login_required
@admin_required
def cleanup():
    result = system_service.run_cleanup()
    return jsonify(result)

@admin_bp.route('/system/backup', methods=['POST'])
@login_required
@super_admin_required
def backup():
    result = system_service.backup_database()
    return jsonify(result)

@admin_bp.route('/system/restore', methods=['POST'])
@login_required
@super_admin_required
def restore():
    file = request.files.get('file')
    result = system_service.restore_database(file)
    return jsonify(result)

@admin_bp.route('/config')
@login_required
@admin_required
def config():
    return render_template('admin/config.html')

@admin_bp.route('/config', methods=['PUT'])
@login_required
@super_admin_required
def update_config():
    data = request.get_json()
    return jsonify({'success': True})

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    from app.models.audit_log import AuditLog
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('admin/logs.html', logs=logs)
