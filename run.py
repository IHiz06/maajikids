"""
MaajiKids Backend — Punto de entrada principal
Ejecutar: python run.py
Producción: gunicorn -w 2 -b 0.0.0.0:5000 "run:app"
"""
import os
from app import create_app

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    print(f"""
╔══════════════════════════════════════════════════════╗
║         MaajiKids Backend API v5.0                  ║
║         Centro de Estimulación Temprana              ║
╠══════════════════════════════════════════════════════╣
║  URL:   http://localhost:{port}                       ║
║  Docs:  http://localhost:{port}/api/docs              ║
║  Health:http://localhost:{port}/health                ║
╚══════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=debug)
