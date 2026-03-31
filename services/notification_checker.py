"""
Background-Checker: Erkennt Zustandsaenderungen und erzeugt Notifications
Laeuft als daemon-Thread alle 60 Sekunden.
Plans-Sync laeuft alle 10 Minuten.
"""
import threading
from services.notification_service import add_notification, load_state, save_state
from services.docker_service import get_docker_containers
from services.cache_service import load_cache

CHECK_INTERVAL = 60  # Sekunden
PLANS_SYNC_EVERY = 10  # Alle X Check-Zyklen (= alle 10 Minuten)
_checker_timer = None
_check_count = 0


def start_checker():
    """Wird einmal beim App-Start aufgerufen"""
    # Erster Check nach 10 Sekunden (App muss erst starten)
    timer = threading.Timer(10, _run_check)
    timer.daemon = True
    timer.start()


def _run_check():
    """Fuehrt alle Checks durch und plant den naechsten"""
    global _checker_timer, _check_count
    _check_count += 1
    try:
        _check_containers()
        _check_sync_conflicts()
        _check_new_projects()
        if _check_count % PLANS_SYNC_EVERY == 0:
            _sync_plans()
            _check_ai_hotspots()
    except Exception:
        pass  # Checker darf niemals den Server crashen

    _checker_timer = threading.Timer(CHECK_INTERVAL, _run_check)
    _checker_timer.daemon = True
    _checker_timer.start()


def _check_containers():
    """Erkennt Container-Status-Aenderungen"""
    containers = get_docker_containers()
    state = load_state()
    prev = state.get('containers', {})

    # Beim ersten Lauf: nur Snapshot speichern, keine Alerts
    if not prev:
        state['containers'] = {c['name']: c.get('status', '') for c in containers}
        save_state(state)
        return

    current = {}
    for c in containers:
        name = c.get('name', '')
        status = c.get('status', '')
        current[name] = status

        prev_status = prev.get(name, '')
        if not prev_status:
            continue  # Neuer Container, kein Alert

        was_running = 'Running' in prev_status or 'Healthy' in prev_status

        if was_running and 'Stopped' in status:
            add_notification(
                'container_down', 'critical',
                f'Container gestoppt: {name}',
                f'{name} ist nicht mehr erreichbar (vorher: {prev_status})',
                container=name
            )
        elif was_running and 'Unhealthy' in status:
            add_notification(
                'container_unhealthy', 'warning',
                f'Container unhealthy: {name}',
                f'{name} meldet Health-Check Fehler',
                container=name
            )

    state['containers'] = current
    save_state(state)


def _check_sync_conflicts():
    """Erkennt neue Git-Sync-Konflikte"""
    cache = load_cache()
    state = load_state()
    prev_sync = state.get('sync_conflicts', set())
    if isinstance(prev_sync, list):
        prev_sync = set(prev_sync)

    current_conflicts = set()
    for name, proj_data in cache.get('projects', {}).items():
        if isinstance(proj_data, dict) and proj_data.get('sync_status') == 'differs':
            current_conflicts.add(name)

    # Nur neue Konflikte melden
    new_conflicts = current_conflicts - prev_sync
    for name in new_conflicts:
        add_notification(
            'sync_conflict', 'warning',
            f'Sync-Konflikt: {name}',
            f'Lokale und Remote-Version von {name} unterscheiden sich',
            project=name
        )

    state['sync_conflicts'] = list(current_conflicts)
    save_state(state)


def _check_new_projects():
    """Erkennt neu hinzugefuegte Projekte"""
    cache = load_cache()
    state = load_state()
    prev_projects = set(state.get('known_projects', []))

    current_projects = set()
    for name in cache.get('projects', {}):
        current_projects.add(name)

    # Beim ersten Lauf: nur Snapshot
    if not prev_projects:
        state['known_projects'] = list(current_projects)
        save_state(state)
        return

    new_projects = current_projects - prev_projects
    for name in new_projects:
        add_notification(
            'new_project', 'info',
            f'Neues Projekt: {name}',
            f'Projekt {name} wurde erkannt',
            project=name
        )

    state['known_projects'] = list(current_projects)
    save_state(state)


def _check_ai_hotspots():
    """Sprint 10.6: Warnt bei Dateien mit hoher AI-Aktivitaet oder Rework-Rate"""
    try:
        from services.db_service import execute, ensure_file_touch_schema
        ensure_file_touch_schema()

        # Dateien mit > 10 AI-Touches in 7 Tagen
        high_touch = execute("""
            SELECT ft.project, ft.file_path, COUNT(*) AS touches
            FROM ai_file_touches ft
            WHERE ft.ai_written = TRUE
                AND ft.timestamp > NOW() - INTERVAL '7 days'
            GROUP BY ft.project, ft.file_path
            HAVING COUNT(*) > 10
            ORDER BY touches DESC
            LIMIT 10
        """, fetch=True)

        for r in (high_touch or []):
            add_notification(
                'ai_hotspot', 'warning',
                f'AI Hotspot: {r["file_path"]}',
                f'{r["file_path"]} was modified {r["touches"]} times by AI in the last 7 days',
                project=r["project"]
            )

        # Dateien mit Rework-Rate > 25% (min 4 Touches)
        high_rework = execute("""
            SELECT ft.project, ft.file_path,
                COUNT(*) AS touches,
                COUNT(*) FILTER (WHERE s.outcome IN ('needs_fix', 'reverted')) AS rework,
                ROUND(COUNT(*) FILTER (WHERE s.outcome IN ('needs_fix', 'reverted'))
                    * 100.0 / COUNT(*), 1) AS rework_pct
            FROM ai_file_touches ft
            JOIN sessions s ON s.id = ft.session_id
            WHERE ft.ai_written = TRUE
                AND ft.timestamp > NOW() - INTERVAL '30 days'
            GROUP BY ft.project, ft.file_path
            HAVING COUNT(*) >= 4
                AND COUNT(*) FILTER (WHERE s.outcome IN ('needs_fix', 'reverted'))
                    * 100.0 / COUNT(*) > 25
            ORDER BY rework_pct DESC
            LIMIT 10
        """, fetch=True)

        for r in (high_rework or []):
            add_notification(
                'ai_hotspot', 'warning',
                f'High rework: {r["file_path"]}',
                f'{r["file_path"]} has {r["rework_pct"]}% rework rate ({r["rework"]}/{r["touches"]} sessions)',
                project=r["project"]
            )
    except Exception:
        pass  # Hotspot-Check darf niemals den Server crashen


def _sync_plans():
    """Synchronisiert Claude Code Plans aus ~/.claude/plans/ in die DB"""
    try:
        from services.plans_import import sync_plans
        stats = sync_plans()
        if stats['imported'] > 0:
            add_notification(
                'new_project', 'info',
                f'{stats["imported"]} neue Plans importiert',
                f'Plans-Sync: {stats["imported"]} neu, {stats["updated"]} aktualisiert',
            )
    except Exception:
        pass  # Plans-Sync darf niemals den Server crashen
