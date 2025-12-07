from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
from app.services.report_service import ReportService

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')
report_service = ReportService()

def analyst_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('analyst'):
            return jsonify({'error': 'Analyst access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@reports_bp.route('/')
@login_required
def dashboard():
    return render_template('reports/dashboard.html')

@reports_bp.route('/generate', methods=['GET'])
@login_required
@analyst_required
def generate_form():
    return render_template('reports/generate.html')

@reports_bp.route('/generate', methods=['POST'])
@login_required
@analyst_required
def generate():
    data = request.get_json()
    report_type = data.get('report_type')
    params = data.get('params', {})
    format_type = data.get('format', 'pdf')
    
    if format_type == 'pdf':
        result = report_service.generate_pdf_report(report_type, params, current_user.id)
    else:
        result = report_service.generate_csv_export(report_type, params)
    
    return jsonify(result)

@reports_bp.route('/download/<filename>')
@login_required
def download(filename):
    return send_file(f'reports/{filename}', as_attachment=True)

@reports_bp.route('/templates')
@login_required
def templates():
    templates = report_service.get_report_templates()
    return jsonify(templates)

@reports_bp.route('/scheduled')
@login_required
def scheduled():
    return render_template('reports/scheduled.html')

@reports_bp.route('/schedule', methods=['POST'])
@login_required
@analyst_required
def schedule():
    data = request.get_json()
    result = report_service.schedule_report(data, current_user.id)
    return jsonify(result)

@reports_bp.route('/scheduled/<int:id>', methods=['DELETE'])
@login_required
@analyst_required
def delete_scheduled(id):
    return jsonify({'success': True})

@reports_bp.route('/audit')
@login_required
@admin_required
def audit():
    filters = {
        'user_id': request.args.get('user_id', type=int),
        'action': request.args.get('action'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date')
    }
    audit_trail = report_service.get_audit_trail(filters)
    return render_template('reports/audit.html', audit_trail=audit_trail)

@reports_bp.route('/audit/export')
@login_required
@admin_required
def audit_export():
    filters = {
        'user_id': request.args.get('user_id', type=int),
        'action': request.args.get('action'),
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date')
    }
    result = report_service.generate_csv_export('audit', filters)
    return jsonify(result)
