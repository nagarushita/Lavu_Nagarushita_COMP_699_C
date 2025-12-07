from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models.alert import AlertRule, Alert
from app.services.alert_service import AlertEngine

alerts_bp = Blueprint('alerts', __name__, url_prefix='/alerts')
alert_engine = AlertEngine()

def analyst_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('analyst'):
            return jsonify({'error': 'Analyst access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@alerts_bp.route('/')
@login_required
def dashboard():
    stats = alert_engine.get_alert_statistics()
    active_alerts = Alert.query.filter_by(status='active').order_by(Alert.triggered_at.desc()).limit(10).all()
    return render_template('alerts/dashboard.html', stats=stats, active_alerts=active_alerts)

@alerts_bp.route('/active')
@login_required
def active():
    alerts = Alert.query.filter_by(status='active').order_by(Alert.triggered_at.desc()).all()
    return render_template('alerts/list.html', alerts=alerts, title='Active Alerts')

@alerts_bp.route('/history')
@login_required
def history():
    alerts = Alert.query.filter(Alert.status.in_(['resolved', 'acknowledged'])).order_by(Alert.triggered_at.desc()).all()
    return render_template('alerts/list.html', alerts=alerts, title='Alert History')

@alerts_bp.route('/<int:id>')
@login_required
def detail(id):
    alert = Alert.query.get_or_404(id)
    return render_template('alerts/detail.html', alert=alert)

@alerts_bp.route('/<int:id>/acknowledge', methods=['POST'])
@login_required
def acknowledge(id):
    result = alert_engine.acknowledge_alert(id, current_user.id)
    return jsonify(result)

@alerts_bp.route('/<int:id>/resolve', methods=['POST'])
@login_required
def resolve(id):
    notes = request.get_json().get('notes', '')
    result = alert_engine.resolve_alert(id, current_user.id, notes)
    return jsonify(result)

@alerts_bp.route('/rules')
@login_required
@analyst_required
def rules():
    rules = AlertRule.query.order_by(AlertRule.created_at.desc()).all()
    return render_template('alerts/rules.html', rules=rules)

@alerts_bp.route('/rules/<int:id>')
@login_required
@analyst_required
def rule_detail(id):
    rule = AlertRule.query.get_or_404(id)
    return render_template('alerts/rule_form.html', rule=rule)

@alerts_bp.route('/rules', methods=['POST'])
@login_required
@analyst_required
def create_rule():
    data = request.get_json()
    rule = AlertRule(
        name=data['name'],
        description=data.get('description'),
        rule_type=data['rule_type'],
        condition=data['condition'],
        threshold_value=data['threshold_value'],
        threshold_unit=data['threshold_unit'],
        severity=data['severity'],
        is_active=data.get('is_active', True),
        notify_email=data.get('notify_email', False),
        escalation_minutes=data.get('escalation_minutes', 10),
        created_by=current_user.id
    )
    db.session.add(rule)
    db.session.commit()
    return jsonify({'success': True, 'id': rule.id})

@alerts_bp.route('/rules/<int:id>', methods=['PUT'])
@login_required
@analyst_required
def update_rule(id):
    rule = AlertRule.query.get_or_404(id)
    data = request.get_json()
    
    rule.name = data.get('name', rule.name)
    rule.description = data.get('description', rule.description)
    rule.threshold_value = data.get('threshold_value', rule.threshold_value)
    rule.severity = data.get('severity', rule.severity)
    rule.is_active = data.get('is_active', rule.is_active)
    
    db.session.commit()
    return jsonify({'success': True})

@alerts_bp.route('/rules/<int:id>', methods=['DELETE'])
@login_required
@analyst_required
def delete_rule(id):
    rule = AlertRule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({'success': True})

@alerts_bp.route('/rules/<int:id>/toggle', methods=['POST'])
@login_required
@analyst_required
def toggle_rule(id):
    rule = AlertRule.query.get_or_404(id)
    rule.is_active = not rule.is_active
    db.session.commit()
    return jsonify({'success': True, 'is_active': rule.is_active})

@alerts_bp.route('/stats')
@login_required
def stats():
    stats = alert_engine.get_alert_statistics()
    
    # Add hourly counts if requested
    range_param = request.args.get('range', '24h')
    hours = int(range_param.replace('h', '')) if 'h' in range_param else 24
    stats['hourly_counts'] = alert_engine.get_hourly_alert_counts(hours)
    
    return jsonify(stats)
