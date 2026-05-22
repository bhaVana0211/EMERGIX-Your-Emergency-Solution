from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, session, current_app)
from app.extensions import db, limiter, oauth
from app.models import User
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ── Helpers ───────────────────────────────────────────────────────────────

def _set_session(user: User):
    session.permanent = True
    session['user_id']    = user.id
    session['username']   = user.username
    session['full_name']  = user.full_name
    session['role']       = user.role if not user.is_management else 'hospital_admin'
    session['hospital_id']= user.hospital_id
    session['avatar_url'] = user.avatar_url or ''


def _make_unique_username(base: str) -> str:
    """Generate a unique username from a base string."""
    base = re.sub(r'[^a-z0-9_]', '', base.lower())[:20] or 'user'
    username = base
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base}{counter}"
        counter += 1
    return username


def _google_configured() -> bool:
    return bool(current_app.config.get('GOOGLE_CLIENT_ID') and
                current_app.config.get('GOOGLE_CLIENT_SECRET'))


# ── Patient Login ─────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute")
def login():
    if session.get('user_id'):
        return redirect(url_for('hospitals.discovery'))
    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password   = request.form.get('password', '')
        user = (User.query.filter_by(email=identifier).first() or
                User.query.filter_by(phone=identifier).first() or
                User.query.filter_by(username=identifier).first())
        if user and user.is_active:
            # Google-only account trying to use password login
            if user.auth_provider == 'google' and not user.password_hash:
                flash('This account uses Google Sign-In. Please click "Continue with Google" below.', 'info')
                return render_template('auth/login.html', google_enabled=_google_configured())
            if user.check_password(password):
                if user.role == 'hospital_admin' or user.is_management:
                    flash('Please use the Hospital Staff login.', 'info')
                    return redirect(url_for('auth.hospital_login'))
                _set_session(user)
                flash(f'Welcome back, {user.full_name.split()[0]}!', 'success')
                return redirect(request.args.get('next') or url_for('hospitals.discovery'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('auth/login.html', google_enabled=_google_configured())


# ── Patient Register ──────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def register():
    if session.get('user_id'):
        return redirect(url_for('hospitals.discovery'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip().lower()
        phone     = request.form.get('phone', '').strip()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

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
                                   form_data={'full_name': full_name, 'email': email, 'phone': phone},
                                   google_enabled=_google_configured())

        user = User(
            full_name=full_name, email=email, phone=phone,
            username=_make_unique_username(full_name),
            role='patient', auth_provider='local',
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        _set_session(user)
        flash(f'Welcome to EMERGIX, {full_name.split()[0]}!', 'success')
        return redirect(url_for('hospitals.discovery'))

    return render_template('auth/register.html', form_data={},
                           google_enabled=_google_configured())


# ── Hospital Admin Login ──────────────────────────────────────────────────

@auth_bp.route('/hospital-login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes", error_message="Too many attempts. Please wait 15 minutes.")
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


# ── Google OAuth ──────────────────────────────────────────────────────────

@auth_bp.route('/google')
def google_login():
    """Redirect to Google consent screen."""
    if not _google_configured():
        flash('Google Sign-In is not configured on this server.', 'warning')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    if not _google_configured():
        flash('Google Sign-In is not configured.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        token = oauth.google.authorize_access_token()
    except Exception as e:
        flash('Google Sign-In was cancelled or failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    user_info = token.get('userinfo')
    if not user_info:
        flash('Could not retrieve your Google profile. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    google_id  = user_info.get('sub')
    email      = user_info.get('email', '').lower()
    full_name  = user_info.get('name', 'Google User')
    avatar_url = user_info.get('picture', '')

    if not email:
        flash('Your Google account does not have a verified email. Please register manually.', 'danger')
        return redirect(url_for('auth.login'))

    # 1. Find by google_id (returning Google user)
    user = User.query.filter_by(google_id=google_id).first()

    # 2. Find by email (existing account — link Google to it)
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            if user.role == 'hospital_admin' or user.is_management:
                flash('Hospital staff accounts cannot use Google Sign-In. Please use the Staff Login page.', 'danger')
                return redirect(url_for('auth.hospital_login'))
            # Link Google to existing account
            user.google_id  = google_id
            user.avatar_url = avatar_url
            if user.auth_provider == 'local':
                user.auth_provider = 'google+local'  # has both
            db.session.commit()

    # 3. Brand-new user — create account automatically
    if not user:
        user = User(
            full_name=full_name,
            email=email,
            username=_make_unique_username(full_name),
            google_id=google_id,
            avatar_url=avatar_url,
            role='patient',
            auth_provider='google',
        )
        db.session.add(user)
        db.session.commit()
        flash(f'Account created! Welcome to EMERGIX, {full_name.split()[0]}!', 'success')
    else:
        # Update avatar in case it changed
        if avatar_url:
            user.avatar_url = avatar_url
            db.session.commit()
        flash(f'Welcome back, {user.full_name.split()[0]}!', 'success')

    _set_session(user)
    return redirect(request.args.get('next') or url_for('hospitals.discovery'))


# ── Logout ────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    role = session.get('role')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.hospital_login') if role == 'hospital_admin'
                   else url_for('main.landing'))
