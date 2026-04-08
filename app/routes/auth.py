from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, redirect, current_app
from flask_login import login_user, logout_user, current_user
from app.extensions import db, limiter, oauth
from app.models import User, ActivityLog
from app.security import (
    record_failed_login, clear_failed_logins, is_ip_locked,
    lockout_remaining, lockout_protected, require_json, validate_input
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def init_google_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name                = 'google',
        client_id           = app.config['GOOGLE_CLIENT_ID'],
        client_secret       = app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url = 'https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs       = {'scope': 'openid email profile'},
    )


def _log(event_type, detail, user_id=None):
    db.session.add(ActivityLog(
        user_id=user_id, event_type=event_type,
        detail=detail, ip_address=request.remote_addr
    ))


# ── Register ──────────────────────────────────────────────────────────────
@auth_bp.post('/register')
@limiter.limit('5 per hour')
@require_json
def register():
    data = request.get_json()

    first_name = data.get('first_name', '').strip()
    last_name  = data.get('last_name',  '').strip()
    email      = data.get('email',      '').strip().lower()
    password   = data.get('password',   '')

    if not all([first_name, last_name, email, password]):
        return jsonify({'error': 'All fields are required'}), 400

    # Input validation
    err = validate_input(data, ['first_name', 'last_name', 'email'])
    if err:
        return jsonify({'error': err}), 400

    # Email format check
    import re
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'error': 'Invalid email address'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    # Password strength: at least one digit and one letter
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return jsonify({'error': 'Password must contain letters and numbers'}), 400

    if len(first_name) > 50 or len(last_name) > 50:
        return jsonify({'error': 'Name too long'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(
        first_name    = first_name,
        last_name     = last_name,
        email         = email,
        storage_quota = current_app.config['DEFAULT_STORAGE_QUOTA'],
    )
    user.set_password(password)
    db.session.add(user)
    _log('register', f'New user: {email}')
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({'message': 'Account created', 'user': user.to_dict()}), 201


# ── Login ─────────────────────────────────────────────────────────────────
@auth_bp.post('/login')
@limiter.limit('20 per hour;5 per minute')
@lockout_protected
@require_json
def login():
    ip   = request.remote_addr
    data = request.get_json()

    email    = data.get('email',    '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    # Validate input for injection
    err = validate_input({'email': email}, ['email'])
    if err:
        record_failed_login(ip)
        return jsonify({'error': 'Invalid input'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        record_failed_login(ip)
        _log('login_fail', f'Failed login: {email}')
        db.session.commit()
        # Remaining attempts hint
        from app.security import LOCKOUT_ATTEMPTS, _login_attempts, LOCKOUT_WINDOW
        from datetime import timedelta
        now     = datetime.now(timezone.utc)
        cutoff  = now - timedelta(seconds=LOCKOUT_WINDOW)
        recent  = [t for t in _login_attempts.get(ip, []) if t > cutoff]
        left    = max(0, LOCKOUT_ATTEMPTS - len(recent))
        msg     = f'Invalid email or password. {left} attempt{"s" if left != 1 else ""} remaining before lockout.' if left > 0 else 'Account temporarily locked.'
        return jsonify({'error': msg}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is disabled. Contact admin.'}), 403

    # Successful login — clear failed attempt tracker
    clear_failed_logins(ip)

    user.last_login = datetime.now(timezone.utc)
    _log('login', f'{email} signed in', user.id)
    db.session.commit()

    login_user(user, remember=True)
    return jsonify({'message': 'Logged in', 'user': user.to_dict(include_stats=True)}), 200


# ── Logout ────────────────────────────────────────────────────────────────
@auth_bp.post('/logout')
def logout():
    if current_user.is_authenticated:
        _log('logout', f'{current_user.email} signed out', current_user.id)
        db.session.commit()
    logout_user()
    return jsonify({'message': 'Logged out'}), 200


# ── Current user ──────────────────────────────────────────────────────────
@auth_bp.get('/me')
def me():
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False}), 401
    return jsonify({'authenticated': True, 'user': current_user.to_dict(include_stats=True)}), 200


# ── Google OAuth ──────────────────────────────────────────────────────────
@auth_bp.get('/google')
def google_login():
    redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.get('/google/callback')
def google_callback():
    try:
        token     = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            return redirect('/login.html?error=google_failed')

        email     = user_info.get('email', '').lower()
        google_id = user_info.get('sub')
        first     = user_info.get('given_name', '')
        last      = user_info.get('family_name', '')
        avatar    = user_info.get('picture', '')

        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            user = User.query.filter_by(email=email).first()

        if user:
            user.google_id  = google_id
            user.avatar_url = avatar
            if not user.is_active:
                return redirect('/login.html?error=account_disabled')
        else:
            user = User(
                first_name    = first or email.split('@')[0],
                last_name     = last or '',
                email         = email,
                google_id     = google_id,
                avatar_url    = avatar,
                storage_quota = current_app.config['DEFAULT_STORAGE_QUOTA'],
            )
            db.session.add(user)
            _log('register', f'Google signup: {email}')

        user.last_login = datetime.now(timezone.utc)
        _log('login', f'{email} signed in via Google', user.id)
        db.session.commit()
        login_user(user, remember=True)

        return redirect('/admin.html' if user.is_admin else '/dashboard.html')

    except Exception as e:
        current_app.logger.error(f'Google OAuth error: {e}')
        return redirect('/login.html?error=google_failed')
