"""Blueprint-Registrierung"""
from routes.session_routes import sessions_bp
from routes.session_review_routes import session_review_bp
from routes.document_routes import documents_bp
from routes.project_routes import project_bp
from routes.project_info_routes import project_info_bp
from routes.data_routes import data_bp
from routes.relation_routes import relation_bp
from routes.group_routes import group_bp
from routes.idea_routes import idea_bp
from routes.news_routes import news_bp
from routes.search_routes import search_bp
from routes.session_analysis_routes import session_analysis_bp
from routes.git_routes import git_bp
from routes.widget_routes import widget_bp
from routes.notification_routes import notification_bp
from routes.timesheet_routes import timesheets_bp
from routes.settings_routes import settings_bp
from routes.scaffold_routes import scaffold_bp
from routes.context_routes import context_bp
from routes.scheduled_tasks_routes import scheduled_tasks_bp
from routes.plans_routes import plans_bp
from routes.quality_routes import quality_bp
from routes.usage_monitor_routes import usage_monitor_bp
from routes.otel_routes import otel_bp
from routes.usage_reports_routes import usage_reports_bp
from routes.session_filter_routes import session_filter_bp
from routes.analytics_routes import analytics_bp
from routes.model_comparison_routes import model_comparison_bp
from routes.governance_routes import governance_bp
from routes.project_memory_routes import project_memory_bp
from routes.audit_routes import audit_bp
from routes.llm_command_routes import llm_commands_bp
from routes.copilot_routes import copilot_bp
from routes.copilot_marker_routes import copilot_marker_bp
from routes.section_routes import section_bp
from routes.model_eval_routes import model_eval_bp
from routes.workflow_routes import workflow_bp
from routes.tool_setup_review_routes import tool_setup_review_bp
from routes.policy_routes import policy_bp
from routes.context_window_optimizer_routes import cwo_bp
from routes.finding_decision_routes import finding_decisions_bp
from routes.review_metrics_routes import review_metrics_bp


def register_blueprints(app):
    app.register_blueprint(sessions_bp)
    app.register_blueprint(session_review_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(project_info_bp)
    app.register_blueprint(relation_bp)
    app.register_blueprint(group_bp)
    app.register_blueprint(idea_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(widget_bp)
    app.register_blueprint(session_analysis_bp)
    app.register_blueprint(git_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(timesheets_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(scaffold_bp)
    app.register_blueprint(context_bp)
    app.register_blueprint(scheduled_tasks_bp)
    app.register_blueprint(plans_bp)
    app.register_blueprint(quality_bp)
    app.register_blueprint(usage_monitor_bp)
    app.register_blueprint(otel_bp)
    app.register_blueprint(usage_reports_bp)
    app.register_blueprint(session_filter_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(model_comparison_bp)
    app.register_blueprint(governance_bp)
    app.register_blueprint(project_memory_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(llm_commands_bp)
    app.register_blueprint(copilot_bp)
    app.register_blueprint(copilot_marker_bp)
    app.register_blueprint(section_bp)
    app.register_blueprint(model_eval_bp)
    app.register_blueprint(workflow_bp)
    app.register_blueprint(tool_setup_review_bp)
    app.register_blueprint(policy_bp)
    app.register_blueprint(cwo_bp)
    app.register_blueprint(finding_decisions_bp)
    app.register_blueprint(review_metrics_bp)
