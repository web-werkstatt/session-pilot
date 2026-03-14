"""Blueprint-Registrierung"""
from routes.session_routes import sessions_bp
from routes.document_routes import documents_bp


def register_blueprints(app):
    app.register_blueprint(sessions_bp)
    app.register_blueprint(documents_bp)
