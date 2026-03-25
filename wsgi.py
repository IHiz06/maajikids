"""
MaajiKids — WSGI entry point (producción)
Usar con: gunicorn -w 2 -b 0.0.0.0:$PORT "wsgi:application"
"""
import os
from app import create_app

application = create_app(os.environ.get("FLASK_ENV", "production"))
app = application  # alias para compatibilidad con gunicorn
