"""Blueprint-Registrierung"""
from routes.session_routes import sessions_bp
from routes.document_routes import documents_bp
from routes.project_routes import project_bp
from routes.data_routes import data_bp
from routes.relation_routes import relation_bp
from routes.group_routes import group_bp
from routes.idea_routes import idea_bp
from routes.news_routes import news_bp
from routes.search_routes import search_bp
from routes.widget_routes import widget_bp


def register_blueprints(app):
    app.register_blueprint(sessions_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(relation_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(idea_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(widget_bp)
