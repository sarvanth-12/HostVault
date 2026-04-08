"""
HostVault Security Middleware
Covers: Security headers, request validation, brute-force tracking, file sanitization
"""
import re
import os
import unicodedata
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import request, jsonify, g
from flask_login import current_user

# ── Allowed file extensions ────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {
    # Documents
    'pdf','doc','docx','xls','xlsx','ppt','pptx','odt','ods','odp','txt','csv','rtf','md',
    # Images
    'jpg','jpeg','png','gif','bmp','webp','svg','ico','tiff',
    # Video
    'mp4','mkv','avi','mov','wmv','flv','webm',
    # Audio
    'mp3','wav','flac','aac','ogg','m4a',
    # Archives
    'zip','rar','7z','tar','gz','bz2',
    # Code / text
    'py','js','ts','html','css','json','xml','yaml','yml','sh','bat','sql',
    # Other
    'apk','iso','dmg',
}

# Dangerous extensions — always blocked
BLOCKED_EXTENSIONS = {
    'exe','msi','bat','cmd','com','vbs','vbe','js','jse','wsf','wsh',
    'ps1','psm1','psd1','scr','pif','reg','inf','lnk','dll','sys',
    'cpl','hta','msc','msp','mst','pif','application',
}

MAX_FILENAME_LENGTH = 255
MAX_FILE_SIZE       = 5 * 1024 ** 3   # 5 GB hard limit


# ── Security headers ────────────────────────────────────────────────────────
def apply_security_headers(response):
    """Add security headers to every response."""
    h = response.headers
    # Prevent MIME sniffing
    h['X-Content-Type-Options']       = 'nosniff'
    # Clickjacking protection
    h['X-Frame-Options']              = 'SAMEORIGIN'
    # XSS protection (legacy browsers)
    h['X-XSS-Protection']             = '1; mode=block'
    # Referrer policy — don't leak URL to external sites
    h['Referrer-Policy']              = 'strict-origin-when-cross-origin'
    # Permissions policy — disable unused browser features
    h['Permissions-Policy']           = 'camera=(), microphone=(), geolocation=(), payment=()'
    # Content Security Policy
    h['Content-Security-Policy']      = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'self';"
    )
    # Remove server fingerprint
    h['Server'] = 'HostVault'
    return response


# ── Request size guard ──────────────────────────────────────────────────────
def check_request_size():
    """Block requests exceeding the max upload size early."""
    content_length = request.content_length
    if content_length and content_length > MAX_FILE_SIZE:
        return jsonify({'error': 'Request too large'}), 413


# ── Filename sanitizer ──────────────────────────────────────────────────────
def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename:
    - Normalize unicode
    - Strip path traversal attempts (../, etc.)
    - Remove dangerous characters
    - Enforce length limit
    - Block dangerous extensions
    """
    if not filename:
        return 'unnamed_file'

    # Normalize unicode
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')

    # Strip path separators (prevent directory traversal)
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')

    # Keep only safe characters
    filename = re.sub(r'[^\w\s\-.]', '', filename).strip()

    # Limit length
    if len(filename) > MAX_FILENAME_LENGTH:
        name, ext = os.path.splitext(filename)
        filename  = name[:MAX_FILENAME_LENGTH - len(ext)] + ext

    if not filename:
        filename = 'unnamed_file'

    # Check extension
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext in BLOCKED_EXTENSIONS:
        filename = filename.rsplit('.', 1)[0] + '.blocked'

    return filename


def is_allowed_file(filename: str) -> bool:
    """Return True if file extension is in the allowed list."""
    if '.' not in filename:
        return True  # No extension — allow (treated as binary)
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in BLOCKED_EXTENSIONS:
        return False
    return True  # Allow anything not explicitly blocked


# ── In-memory brute force tracker ──────────────────────────────────────────
_login_attempts: dict[str, list] = {}   # ip -> [timestamp, ...]
LOCKOUT_ATTEMPTS = 10        # max failed attempts
LOCKOUT_WINDOW   = 600       # 10 minute window (seconds)
LOCKOUT_DURATION = 900       # 15 minute lockout (seconds)


def record_failed_login(ip: str):
    now = datetime.now(timezone.utc)
    attempts = _login_attempts.setdefault(ip, [])
    attempts.append(now)
    # Keep only attempts within the window
    cutoff = now - timedelta(seconds=LOCKOUT_WINDOW)
    _login_attempts[ip] = [t for t in attempts if t > cutoff]


def is_ip_locked(ip: str) -> bool:
    now      = datetime.now(timezone.utc)
    cutoff   = now - timedelta(seconds=LOCKOUT_DURATION)
    attempts = _login_attempts.get(ip, [])
    recent   = [t for t in attempts if t > cutoff]
    return len(recent) >= LOCKOUT_ATTEMPTS


def clear_failed_logins(ip: str):
    _login_attempts.pop(ip, None)


def lockout_remaining(ip: str) -> int:
    """Return seconds remaining in lockout, or 0 if not locked."""
    now      = datetime.now(timezone.utc)
    attempts = _login_attempts.get(ip, [])
    if not attempts:
        return 0
    cutoff = now - timedelta(seconds=LOCKOUT_DURATION)
    recent = [t for t in attempts if t > cutoff]
    if len(recent) < LOCKOUT_ATTEMPTS:
        return 0
    oldest_recent = min(recent)
    remaining = (oldest_recent + timedelta(seconds=LOCKOUT_DURATION) - now).seconds
    return max(0, remaining)


# ── SQL injection / XSS input sanitizer ────────────────────────────────────
_SQL_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|CAST|CONVERT)\b)",
    r"(--|;|/\*|\*/)",
    r"(\bOR\b\s+[\w'\"]+\s*=\s*[\w'\"]+)",
    r"(\bAND\b\s+[\w'\"]+\s*=\s*[\w'\"]+)",
]
_SQL_RE = re.compile('|'.join(_SQL_PATTERNS), re.IGNORECASE)

_XSS_PATTERNS = [
    r"<script[\s\S]*?>[\s\S]*?</script>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<\s*iframe",
    r"<\s*object",
    r"<\s*embed",
    r"eval\s*\(",
    r"expression\s*\(",
]
_XSS_RE = re.compile('|'.join(_XSS_PATTERNS), re.IGNORECASE)


def contains_sql_injection(value: str) -> bool:
    return bool(_SQL_RE.search(value))


def contains_xss(value: str) -> bool:
    return bool(_XSS_RE.search(value))


def validate_input(data: dict, fields: list[str]) -> str | None:
    """
    Check specified fields for SQL injection or XSS.
    Returns an error string if found, else None.
    """
    for field in fields:
        val = str(data.get(field, ''))
        if contains_sql_injection(val):
            return f'Invalid characters in {field}'
        if contains_xss(val):
            return f'Invalid content in {field}'
    return None


# ── Decorator: block locked IPs on login ───────────────────────────────────
def lockout_protected(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr
        if is_ip_locked(ip):
            remaining = lockout_remaining(ip)
            return jsonify({
                'error': f'Too many failed attempts. Try again in {remaining // 60} min {remaining % 60} sec.'
            }), 429
        return f(*args, **kwargs)
    return wrapper


# ── Decorator: require JSON body ───────────────────────────────────────────
def require_json(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 415
        return f(*args, **kwargs)
    return wrapper


# ── Register all security hooks on the Flask app ───────────────────────────
def init_security(app):
    app.after_request(apply_security_headers)
    app.before_request(check_request_size)

    # Log suspicious requests
    @app.before_request
    def detect_suspicious():
        ua = request.headers.get('User-Agent', '')
        # Block empty user agents on API routes
        if request.path.startswith('/api/') and not ua:
            return jsonify({'error': 'Bad request'}), 400
        # Block common scanner user agents
        scanners = ['sqlmap', 'nikto', 'nmap', 'masscan', 'zgrab', 'dirbuster', 'hydra']
        if any(s in ua.lower() for s in scanners):
            return jsonify({'error': 'Forbidden'}), 403
