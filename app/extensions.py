from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from authlib.integrations.flask_client import OAuth

db            = SQLAlchemy()
login_manager = LoginManager()
limiter       = Limiter(key_func=get_remote_address)
cors          = CORS()
oauth         = OAuth()
