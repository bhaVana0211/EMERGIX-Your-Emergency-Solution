from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.extensions import db, limiter
from app.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if session.get('user_id'):
        return redirect(url_for('hospitals.discovery'))
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')
        user = (User.query.filter_by(email=identifier).first() or
                User.query.filter_by(phone=identifier).first() or
                User.query.filter_by(username=identifier).first())
        if user and user.check_password(password) and user.is_active:
            if user.role == 'hospital_admin' or user.is_management:
                flash('Please use the Hospital Staff login.', 'info')
                return redirect(url_for('auth.hospital_login'))
            _set_session(user)
            flash(f'Welcome back, {user.full_name.split()[0]}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('hospitals.discovery'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def register():
    if session.get('user_id'):
        return redirect(url_for('hospitals.discovery'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not full_name or len(full_name) < 2:
            errors.append('Full name must be at least 2 characters.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not phone or len(phone) < 10:
            errors.append('A valid 10-digit phone number is required.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')
        if User.query.filter_by(email=email).first():
            errors.append('An account with this email already exists.')
        if User.query.filter_by(phone=phone).first():
            errors.append('An account with this phone number already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('auth/register.html',
                                   form_data={'full_name': full_name, 'email': email, 'phone': phone})

        username = email.split('@')[0] + str(User.query.count() + 1)
        user = User(full_name=full_name, email=email, phone=phone,
                    username=username, role='patient')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        _set_session(user)
        flash(f'Welcome to EMERGIX, {full_name.split()[0]}!', 'success')
        return redirect(url_for('hospitals.discovery'))
    return render_template('auth/register.html', form_data={})


@auth_bp.route('/hospital-login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes", error_message="Too many login attempts. Please wait 15 minutes.")
def hospital_login():
    if session.get('user_id') and session.get('role') == 'hospital_admin':
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active:
            if user.role == 'hospital_admin' or user.is_management:
                _set_session(user)
                flash(f'Welcome back, {user.full_name.split()[0]}!', 'success')
                return redirect(url_for('admin.dashboard'))
        flash('Invalid staff credentials. Access denied.', 'danger')
    return render_template('auth/hospital_login.html')


@auth_bp.route('/logout')
def logout():
    role = session.get('role')
    session.clear()
    flash('You have been logged out.', 'info')
    if role == 'hospital_admin':
        return redirect(url_for('auth.hospital_login'))
    return redirect(url_for('main.landing'))


def _set_session(user: User):
    session['user_id'] = user.id
    session['username'] = user.username
    session['full_name'] = user.full_name
    session['role'] = user.role if not user.is_management else 'hospital_admin'
    session['hospital_id'] = user.hospital_id
    session.permanent = True
