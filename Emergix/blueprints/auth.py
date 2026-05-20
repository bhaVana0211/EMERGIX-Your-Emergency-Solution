"""
EMERGIX — Auth Blueprint
Patient login/register, Hospital admin login, Logout.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from Emergix.models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Patient / general user login."""
    if session.get('user_id'):
        if session.get('role') == 'hospital_admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('hospitals.discovery'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        # Allow login by username, email, or phone
        user = User.query.filter(
            (User.username == login_id) |
            (User.email == login_id) |
            (User.phone == login_id)
        ).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['is_management'] = user.is_management  # backward compatibility
            if user.hospital_id:
                session['hospital_id'] = user.hospital_id
            if user.role == 'hospital_admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('hospitals.discovery'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Patient registration."""
    if session.get('user_id'):
        return redirect(url_for('hospitals.discovery'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validation
        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not email:
            errors.append('Email is required.')
        if not phone or len(phone) != 10 or not phone.isdigit():
            errors.append('Please enter a valid 10-digit phone number.')
        if len(password) < 8:
            errors.append('Password must be at least 8 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')

        # Check uniqueness
        if User.query.filter_by(username=username).first():
            errors.append('Username already taken.')
        if email and User.query.filter_by(email=email).first():
            errors.append('Email already registered.')
        if phone and User.query.filter_by(phone=phone).first():
            errors.append('Phone number already registered.')

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('auth/register.html',
                                   username=username, email=email, phone=phone)

        # Create user
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            role='patient',
            is_management=False
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Auto-login after registration
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        session['role'] = 'patient'
        session['is_management'] = False

        flash('Registration successful! Welcome to EMERGIX.', 'success')
        return redirect(url_for('hospitals.discovery'))

    return render_template('auth/register.html')


@auth_bp.route('/hospital-login', methods=['GET', 'POST'])
def hospital_login():
    """Hospital admin login — visually distinct page."""
    if session.get('user_id') and session.get('role') == 'hospital_admin':
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and (user.role == 'hospital_admin' or user.is_management):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = 'hospital_admin'
            session['is_management'] = True
            if user.hospital_id:
                session['hospital_id'] = user.hospital_id
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('auth/hospital_login.html')


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to landing page."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.landing'))


@auth_bp.route('/google')
def google_login():
    """Redirect to Google OAuth consent screen."""
    from Emergix.oauth import oauth
    if not oauth.google:
        flash('Google Login is not configured.', 'danger')
        return redirect(url_for('auth.login'))
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback and log the user in."""
    from Emergix.oauth import oauth
    import random
    import string
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            user_info = oauth.google.userinfo()
    except Exception as e:
        flash('Google login failed.', 'danger')
        return redirect(url_for('auth.login'))
        
    email = user_info.get('email')
    name = user_info.get('name')
    
    if not email:
        flash('Google account has no email associated.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Create a new user using the Google info
        # Generate a random username base and dummy phone
        base_username = email.split('@')[0]
        username = base_username
        
        # Ensure username uniqueness
        while User.query.filter_by(username=username).first():
            username = base_username + ''.join(random.choices(string.digits, k=4))
            
        new_user = User(
            username=username,
            email=email,
            phone='0000000000', # Dummy phone, prompt user to update profile later
            role='patient',
            is_management=False
        )
        new_user.set_password(''.join(random.choices(string.ascii_letters + string.digits, k=16)))
        db.session.add(new_user)
        db.session.commit()
        user = new_user
        flash('Account created successfully via Google!', 'success')
    else:
        flash(f'Welcome back, {user.username}!', 'success')

    # Log them in
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    session['is_management'] = user.is_management
    
    return redirect(url_for('hospitals.discovery'))
