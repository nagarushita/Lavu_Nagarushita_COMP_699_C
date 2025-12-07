from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.services.analysis_service import AnalysisService, HistoricalQueryService

analysis_bp = Blueprint('analysis', __name__, url_prefix='/analysis')
analysis_service = AnalysisService()
historical_service = HistoricalQueryService()

def analyst_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('analyst'):
            return jsonify({'error': 'Analyst access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@analysis_bp.route('/')
@login_required
@analyst_required
def dashboard():
    return render_template('analysis/dashboard.html')

@analysis_bp.route('/dns')
@login_required
@analyst_required
def dns():
    data = analysis_service.analyze_dns()
    return render_template('analysis/dns.html', data=data)

@analysis_bp.route('/dhcp')
@login_required
@analyst_required
def dhcp():
    data = analysis_service.analyze_dhcp()
    return render_template('analysis/dhcp.html', data=data)

@analysis_bp.route('/tcp')
@login_required
@analyst_required
def tcp():
    data = analysis_service.analyze_tcp_states()
    return render_template('analysis/tcp.html', data=data)

@analysis_bp.route('/http')
@login_required
@analyst_required
def http():
    data = analysis_service.analyze_http()
    return render_template('analysis/http.html', data=data)

@analysis_bp.route('/https')
@login_required
@analyst_required
def https():
    data = analysis_service.analyze_https()
    return render_template('analysis/https.html', data=data)

@analysis_bp.route('/email')
@login_required
@analyst_required
def email():
    data = analysis_service.analyze_email()
    return render_template('analysis/email.html', data=data)

@analysis_bp.route('/p2p')
@login_required
@analyst_required
def p2p():
    data = analysis_service.detect_p2p()
    return render_template('analysis/p2p.html', data=data)

@analysis_bp.route('/custom')
@login_required
@analyst_required
def custom():
    return render_template('analysis/custom.html')

@analysis_bp.route('/run', methods=['POST'])
@login_required
@analyst_required
def run():
    data = request.get_json()
    analysis_type = data.get('type')
    params = data.get('params', {})
    result = analysis_service.get_protocol_summary(params.get('time_range', '24h'))
    return jsonify(result)

@analysis_bp.route('/export/<type>')
@login_required
@analyst_required
def export(type):
    return jsonify({'success': True, 'file': f'{type}_export.csv'})

@analysis_bp.route('/historical')
@login_required
@analyst_required
def historical():
    return render_template('analysis/historical.html')

@analysis_bp.route('/historical/search', methods=['POST'])
@login_required
@analyst_required
def historical_search():
    data = request.get_json()
    criteria = data.get('criteria', [])
    results = historical_service.search_traffic(criteria)
    return jsonify(results)

@analysis_bp.route('/historical/results/<qid>')
@login_required
@analyst_required
def historical_results(qid):
    return jsonify({'query_id': qid, 'results': []})

@analysis_bp.route('/baseline')
@login_required
@analyst_required
def baseline():
    return render_template('analysis/baseline.html')

@analysis_bp.route('/baseline/compare', methods=['POST'])
@login_required
@analyst_required
def baseline_compare():
    data = request.get_json()
    current = data.get('current')
    baseline = data.get('baseline')
    results = historical_service.compare_baseline(current, baseline)
    return jsonify(results)

@analysis_bp.route('/trends')
@login_required
@analyst_required
def trends():
    return render_template('analysis/trends.html')

@analysis_bp.route('/trends/<metric>')
@login_required
@analyst_required
def trends_metric(metric):
    time_range = request.args.get('range', '30d')
    data = historical_service.analyze_trends(metric, time_range)
    return jsonify(data)

@analysis_bp.route('/forensic/export', methods=['POST'])
@login_required
@analyst_required
def forensic_export():
    data = request.get_json()
    session_id = data.get('session_id')
    format_type = data.get('format', 'pcap')
    result = historical_service.export_forensic_data(session_id, format_type)
    return jsonify(result)
