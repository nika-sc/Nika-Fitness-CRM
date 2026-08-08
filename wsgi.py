"""WSGI entrypoint (gunicorn)."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.config import config

env = os.environ.get('FLASK_ENV', 'production')
app = create_app(config.get(env, config['default']))
