from waitress import serve
from app import create_app
from app.config import Config

app = create_app()

# Auto-create database tables on startup
with app.app_context():
    from app.extensions import db
    db.create_all()

if __name__ == '__main__':
    print(f"""
╔══════════════════════════════════════════╗
║         PrivCloud — Starting up          ║
╠══════════════════════════════════════════╣
║  URL  : http://localhost:{Config.PORT}         
║  API  : http://localhost:{Config.PORT}/api     
╚══════════════════════════════════════════╝
    """)
    serve(app, host=Config.HOST, port=Config.PORT, threads=8)