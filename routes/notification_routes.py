"""
Notification API Routes
"""
from flask import Blueprint, jsonify, request
from services.notification_service import (
    load_notifications, get_unread_count,
    mark_read, mark_all_read, dismiss,
)

notification_bp = Blueprint('notifications', __name__)


@notification_bp.route('/api/notifications')
def api_notifications():
    """Alle Notifications (optional nur ungelesene)"""
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    notifications = load_notifications()
    if unread_only:
        notifications = [n for n in notifications if not n.get('read')]
    # Neueste zuerst
    notifications.reverse()
    return jsonify({"notifications": notifications, "total": len(notifications)})


@notification_bp.route('/api/notifications/count')
def api_notification_count():
    """Nur unread-Count (leichtgewichtig fuer Badge-Polling)"""
    return jsonify({"unread": get_unread_count()})


@notification_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
def api_mark_read(notification_id):
    if mark_read(notification_id):
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


@notification_bp.route('/api/notifications/read-all', methods=['POST'])
def api_mark_all_read():
    mark_all_read()
    return jsonify({"success": True})


@notification_bp.route('/api/notifications/<notification_id>', methods=['DELETE'])
def api_dismiss(notification_id):
    dismiss(notification_id)
    return jsonify({"success": True})
