"""Blueprint-Registrierung"""
from routes.session_routes import sessions_bp


def register_blueprints(app):
    app.register_blueprint(sessions_bp)
