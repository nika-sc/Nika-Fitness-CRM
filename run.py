"""Точка входа Nika Fitness CRM."""
import logging
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.config import config

env = os.environ.get('FLASK_ENV', 'development')
app = create_app(config.get(env, config['default']))

if __name__ == '__main__':
    app.config['DEBUG'] = False
    app.logger.setLevel(logging.INFO)
    host = os.environ.get('APP_HOST', '127.0.0.1')
    port = int(os.environ.get('APP_PORT', '5001'))
    sys.stderr.write(f"Nika Fitness CRM → http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, use_reloader=False)
