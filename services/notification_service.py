"""
Notification Store - JSON-basierte Benachrichtigungsverwaltung
Thread-safe via Lock fuer gleichzeitigen Zugriff (Checker-Thread + Flask-Requests)
"""
import os
import json
import uuid
import threading
from datetime import datetime, timedelta

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTIFICATIONS_FILE = os.path.join(_BASE_DIR, 'notifications.json')
STATE_FILE = os.path.join(_BASE_DIR, '.notification_state.json')
MAX_NOTIFICATIONS = 200
DEDUP_WINDOW_HOURS = 1

_lock = threading.Lock()


def load_notifications():
    """Liest alle Notifications aus der JSON-Datei"""
    with _lock:
        if os.path.exists(NOTIFICATIONS_FILE):
            try:
                with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
    return []


def save_notifications(notifications):
    """Speichert Notifications (max MAX_NOTIFICATIONS, FIFO)"""
    with _lock:
        # Auf Maximum begrenzen (neueste behalten)
        if len(notifications) > MAX_NOTIFICATIONS:
            notifications = notifications[-MAX_NOTIFICATIONS:]
        try:
            with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, indent=2, ensure_ascii=False)
        except OSError:
            pass


def add_notification(ntype, severity, title, message, project=None, container=None):
    """Fuegt eine neue Notification hinzu mit Deduplizierung

    Args:
        ntype: container_down, container_unhealthy, new_commit, sync_conflict, new_project
        severity: critical, warning, info
        title: Kurztitel
        message: Detailtext
        project: Projektname (optional)
        container: Containername (optional)
    """
    notifications = load_notifications()

    # Deduplizierung: gleicher type+project+container innerhalb DEDUP_WINDOW
    cutoff = (datetime.now() - timedelta(hours=DEDUP_WINDOW_HOURS)).isoformat()
    for n in notifications[-50:]:
        if (n.get('type') == ntype and n.get('project') == project
                and n.get('container') == container
                and n.get('created_at', '') > cutoff):
            return None  # Duplikat

    notification = {
        'id': uuid.uuid4().hex[:12],
        'type': ntype,
        'severity': severity,
        'title': title,
        'message': message,
        'project': project,
        'container': container,
        'created_at': datetime.now().isoformat(),
        'read': False,
    }
    notifications.append(notification)
    save_notifications(notifications)
    return notification


def get_unread_count():
    """Zaehlt ungelesene Notifications (leichtgewichtig)"""
    notifications = load_notifications()
    return sum(1 for n in notifications if not n.get('read'))


def mark_read(notification_id):
    """Markiert eine Notification als gelesen"""
    notifications = load_notifications()
    for n in notifications:
        if n['id'] == notification_id:
            n['read'] = True
            save_notifications(notifications)
            return True
    return False


def mark_all_read():
    """Markiert alle als gelesen"""
    notifications = load_notifications()
    for n in notifications:
        n['read'] = True
    save_notifications(notifications)


def dismiss(notification_id):
    """Entfernt eine Notification"""
    notifications = load_notifications()
    notifications = [n for n in notifications if n.get('id') != notification_id]
    save_notifications(notifications)


def load_state():
    """Liest den letzten bekannten Zustand fuer Vergleiche"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(state):
    """Speichert den aktuellen Zustand"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
