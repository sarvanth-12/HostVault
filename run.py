from waitress import serve
from app import create_app
from app.config import Config

app = create_app()

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
