import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ── Core ────────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    DEBUG      = os.environ.get('FLASK_DEBUG', '0') == '1'

    # ── Database ─────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI        = os.environ.get('DATABASE_URL', '')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS      = {
        'pool_pre_ping':    True,
        'pool_recycle':     300,
        'pool_size':        10,
        'max_overflow':     20,
    }

    # ── MinIO ─────────────────────────────────────────────────
    MINIO_ENDPOINT   = os.environ.get('MINIO_ENDPOINT',   'localhost:9000')
    MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET     = os.environ.get('MINIO_BUCKET',     'hostvault-files')
    MINIO_SECURE     = os.environ.get('MINIO_SECURE', 'True').lower() == 'true'
    MINIO_REGION     = os.environ.get('MINIO_REGION', 'us-east-005')

    # ── Google OAuth ──────────────────────────────────────────
    GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID',     '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI  = os.environ.get('FRONTEND_URL', 'http://localhost') + '/api/auth/google/callback'

    # ── Rate limiting ─────────────────────────────────────────
    RATELIMIT_DEFAULT     = '300 per day;100 per hour;20 per minute'
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY    = 'fixed-window'
    RATELIMIT_HEADERS_ENABLED = True   # send X-RateLimit headers to client

    # ── Session & Cookie security ─────────────────────────────
    SESSION_COOKIE_HTTPONLY  = True    # JS cannot read session cookie
    SESSION_COOKIE_SAMESITE  = 'Lax'  # CSRF protection
    SESSION_COOKIE_SECURE    = False   # set True when HTTPS is enabled
    SESSION_COOKIE_NAME      = 'hv_session'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 8   # 8 hours

    REMEMBER_COOKIE_HTTPONLY  = True
    REMEMBER_COOKIE_SAMESITE  = 'Lax'
    REMEMBER_COOKIE_SECURE    = False  # set True when HTTPS is enabled
    REMEMBER_COOKIE_DURATION  = 60 * 60 * 24 * 7   # 7 days

    # ── Upload limits ─────────────────────────────────────────
    MAX_CONTENT_LENGTH = 5 * 1024 ** 3   # 5 GB max upload

    # ── App settings ──────────────────────────────────────────
    DEFAULT_STORAGE_QUOTA = int(os.environ.get('DEFAULT_STORAGE_QUOTA', 10 * 1024 ** 3))
    TRASH_RETENTION_DAYS  = int(os.environ.get('TRASH_RETENTION_DAYS', 30))
    FRONTEND_URL          = os.environ.get('FRONTEND_URL', 'http://localhost')
    HOST                  = os.environ.get('HOST', '0.0.0.0')
    PORT                  = int(os.environ.get('PORT', 8000))
