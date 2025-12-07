from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.audit_log import AuditLog
from functools import wraps

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('admin'):
            flash('Admin access required', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        mfa_token = request.form.get('mfa_token')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.failed_login_attempts >= 5:
                flash('Account locked due to too many failed attempts', 'error')
                return render_template('auth/login.html')
            
            if user.mfa_enabled:
                if not mfa_token:
                    return render_template('auth/login.html', show_mfa=True, username=username)
                if not user.verify_mfa_token(mfa_token):
                    flash('Invalid MFA token', 'error')
                    return render_template('auth/login.html', show_mfa=True, username=username)
            
            user.failed_login_attempts = 0
            user.last_login = db.func.now()
            db.session.commit()
            
            login_user(user, remember=remember)
            
            # Create audit log
            audit = AuditLog(user_id=user.id, action='login', resource_type='auth',
                           ip_address=request.remote_addr, user_agent=request.user_agent.string)
            db.session.add(audit)
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard.index'))
        else:
            if user:
                user.failed_login_attempts += 1
                db.session.commit()
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    audit = AuditLog(user_id=current_user.id, action='logout', resource_type='auth',
                   ip_address=request.remote_addr, user_agent=request.user_agent.string)
    db.session.add(audit)
    db.session.commit()
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'viewer')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('auth/register.html')
        
        user = User(username=username, email=email, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('User created successfully', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html')

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            
            if not current_user.check_password(old_password):
                flash('Current password is incorrect', 'error')
            elif len(new_password) < 8:
                flash('Password must be at least 8 characters', 'error')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully', 'success')
    
    return render_template('auth/profile.html')

@auth_bp.route('/mfa/setup', methods=['GET', 'POST'])
@login_required
def mfa_setup():
    if request.method == 'POST':
        token = request.form.get('token')
        if not current_user.mfa_secret:
            current_user.generate_mfa_secret()
            db.session.commit()
        
        if current_user.verify_mfa_token(token):
            current_user.mfa_enabled = True
            db.session.commit()
            flash('MFA enabled successfully', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Invalid token', 'error')
    
    if not current_user.mfa_secret:
        current_user.generate_mfa_secret()
        db.session.commit()
    
    mfa_uri = current_user.get_mfa_uri()
    return render_template('auth/mfa_setup.html', mfa_uri=mfa_uri, secret=current_user.mfa_secret)

@auth_bp.route('/mfa/disable', methods=['POST'])
@login_required
def mfa_disable():
    password = request.form.get('password')
    if current_user.check_password(password):
        current_user.mfa_enabled = False
        current_user.mfa_secret = None
        db.session.commit()
        flash('MFA disabled successfully', 'success')
    else:
        flash('Invalid password', 'error')
    return redirect(url_for('auth.profile'))
