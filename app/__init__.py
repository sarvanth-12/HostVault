from flask import Flask, send_from_directory, jsonify
from app.config import Config
from app.extensions import db, login_manager, limiter, cors, oauth
from app.security import init_security
import os


def create_app():
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, resources={r'/api/*': {
        'origins': [Config.FRONTEND_URL, 'http://localhost', 'http://localhost:8000', 'http://127.0.0.1:8000'],
        'supports_credentials': True,
    }})

    # ── Security middleware ──────────────────────────────────
    init_security(app)

    login_manager.login_view = None

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'error': 'Authentication required'}), 401

    from app.routes.auth import init_google_oauth
    init_google_oauth(app)

    from app.routes import auth_bp, files_bp, trash_bp, profile_bp, admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(trash_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)

    @app.get('/health')
    def public_health():
        return jsonify({'status': 'ok'}), 200

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        full = os.path.join(app.static_folder, path)
        if path and os.path.exists(full):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    return app
