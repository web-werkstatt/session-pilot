"""
Import von Claude Code Plans aus ~/.claude/plans/ in die Datenbank.
Erkennt Projekt-Zuordnung aus Dateiinhalten und verknuepft mit Sessions.
"""
import os
import re
import hashlib
from datetime import datetime, timezone
from services.db_service import execute, ensure_plans_schema


from config import PROJECTS_DIR

PLANS_DIR = os.path.expanduser("~/.claude/plans")

# Regex fuer Projekt-Erkennung aus Plan-Inhalt (matches PROJECTS_DIR/name/)
PROJECT_PATH_RE = re.compile(re.escape(PROJECTS_DIR) + r'/([a-zA-Z0-9_-]+)/')


def _get_known_projects():
    """Liest alle Projektnamen aus /mnt/projects/ und erzeugt Suchvarianten."""
    projects = {}
    try:
        for name in os.listdir(PROJECTS_DIR):
            path = os.path.join(PROJECTS_DIR, name)
            if not os.path.isdir(path) or name.startswith('.'):
                continue
            # Varianten: Original, Bindestrich, Unterstrich, ohne Prefix
            variants = [name, name.replace('_', '-'), name.replace('-', '_')]
            # Lesbarer Name (ohne proj_, tool_ etc.)
            for prefix in ('proj_', 'proj-', 'tool_', 'app_'):
                if name.startswith(prefix):
                    clean = name[len(prefix):]
                    variants.extend([clean, clean.replace('_', '-'), clean.replace('-', '_'),
                                     clean.replace('-', ' '), clean.replace('_', ' ')])
            # Alle Varianten zeigen auf den echten Projektnamen
            for v in variants:
                if len(v) >= 3:  # Zu kurze Varianten ignorieren
                    projects[v.lower()] = name
    except OSError:
        pass
    return projects


def file_hash(filepath):
    """MD5-Hash einer Datei fuer Aenderungserkennung."""
    h = hashlib.md5()
    with open(filepath, 'rb') as f:
        h.update(f.read())
    return h.hexdigest()


def extract_title(content):
    """Extrahiert den Titel aus der ersten H1-Zeile."""
    for line in content.split('\n')[:10]:
        line = line.strip()
        if line.startswith('# '):
            title = line[2:].strip()
            # "Plan: XYZ" -> "XYZ" kuerzen
            if title.lower().startswith('plan:'):
                title = title[5:].strip()
            return title
    return None


def extract_context(content):
    """Extrahiert die Context-Section als Zusammenfassung."""
    lines = content.split('\n')
    in_context = False
    context_lines = []
    for line in lines:
        if re.match(r'^##\s+Context', line, re.IGNORECASE):
            in_context = True
            continue
        if in_context:
            if line.startswith('## ') or line.startswith('# '):
                break
            if line.strip():
                context_lines.append(line.strip())
    return ' '.join(context_lines)[:500] if context_lines else None


def detect_project(content):
    """Erkennt das Projekt aus dem Plan-Inhalt.

    Strategie:
    1. Explizite /mnt/projects/XXX Pfade (hoechste Zuverlaessigkeit)
    2. Projektnamen-Abgleich mit /mnt/projects/ Verzeichnissen
       - Sucht Titel und Context nach bekannten Projektnamen
       - Beruecksichtigt Varianten (Bindestrich, Unterstrich, ohne Prefix)
    """
    # 1. Explizite /mnt/projects/XXX Pfade
    matches = PROJECT_PATH_RE.findall(content)
    if matches:
        from collections import Counter
        counts = Counter(matches)
        return counts.most_common(1)[0][0]

    # 2. Dynamischer Abgleich mit tatsaechlichen Projektnamen
    known = _get_known_projects()
    content_lower = content.lower()

    # Pass 1: Titel + Context (hohe Zuverlaessigkeit)
    title = extract_title(content) or ''
    context = extract_context(content) or ''
    search_text = (title + ' ' + context).lower()

    for variant in sorted(known.keys(), key=len, reverse=True):
        if len(variant) < 5:
            continue
        if variant in search_text:
            return known[variant]

    # Pass 2: Gesamter Inhalt - nur laengere/spezifische Namen (>= 8 Zeichen)
    for variant in sorted(known.keys(), key=len, reverse=True):
        if len(variant) < 8:
            continue
        if variant in content_lower:
            return known[variant]

    # Pass 3: Dateipfade wie static/, templates/, frontend/src/ etc.
    path_hints = [
        (r'templates/.*\.html', 'project_dashboard'),
        (r'static/(css|js)/', 'project_dashboard'),
        (r'routes/.*_routes\.py', 'project_dashboard'),
    ]
    for pattern, project in path_hints:
        if re.search(pattern, content):
            return project

    # Pass 4: Domain-spezifische Begriffe (nur im gesamten Inhalt)
    domain_hints = [
        (['ir-tours', 'ir tours', 'irtours', 'reisen', 'reise-detail',
          'astro.*ssr', 'destination.*landing', 'cms-qualit'], 'proj_irtours'),
        (['collection.*singleton', 'payload.*cms', 'content-systeme',
          'contypio'], 'proj_contypio'),
        (['steuerrecht', 'ear-kennzahl', 'buchh'], 'steuerrecht-api'),
        (['seo.*suite', 'ai.*seo', 'collector.*dashboard.*reporter'], 'proj_seo-suite'),
    ]
    for keywords, project in domain_hints:
        for kw in keywords:
            if re.search(kw, content_lower):
                return project

    return None


def detect_category(content, title):
    """Erkennt die Kategorie aus Inhalt und Titel."""
    text = (title or '').lower() + ' ' + content[:500].lower()
    if any(w in text for w in ['bugfix', 'bug fix', 'fix:', 'fehler', 'broken']):
        return 'bugfix'
    if any(w in text for w in ['refactor', 'redesign', 'aufraeum', 'cleanup']):
        return 'refactor'
    if any(w in text for w in ['setup', 'einrichten', 'install', 'deploy', 'server']):
        return 'infra'
    if any(w in text for w in ['feature', 'neues', 'hinzufueg', 'erstell', 'implement']):
        return 'feature'
    return 'plan'


def _build_session_name_variants(project_name):
    """Erzeugt alle moeglichen Session-Projektnamen fuer einen Plan-Projektnamen.

    Plan-Import erkennt z.B. 'project_dashboard' aus /mnt/projects/project_dashboard/
    Sessions speichern aber 'project-dashboard' (aus dem Verzeichnis-Hash).
    """
    if not project_name:
        return []
    variants = [project_name]
    # Unterstrich <-> Bindestrich
    variants.append(project_name.replace('_', '-'))
    variants.append(project_name.replace('-', '_'))
    # Mit proj- Prefix (haeufig in Sessions)
    variants.append(f"proj-{project_name}")
    variants.append(f"proj-{project_name.replace('_', '-')}")
    variants.append(f"proj-{project_name.replace('-', '')}")
    # Ohne Prefix falls Plan schon proj- hat
    if project_name.startswith('proj-'):
        variants.append(project_name[5:])
        variants.append(project_name[5:].replace('-', '_'))
    return list(set(variants))


def find_related_session(project_name, plan_mtime):
    """Findet die Session die zeitlich am naechsten zum Plan liegt."""
    if not project_name:
        return None
    dt = datetime.fromtimestamp(plan_mtime, tz=timezone.utc)
    variants = _build_session_name_variants(project_name)
    placeholders = ','.join(['%s'] * len(variants))
    rows = execute(
        f"""SELECT session_uuid FROM sessions
           WHERE project_name IN ({placeholders})
             AND started_at BETWEEN %s - INTERVAL '2 hours' AND %s + INTERVAL '1 hour'
           ORDER BY ABS(EXTRACT(EPOCH FROM (started_at - %s)))
           LIMIT 1""",
        variants + [dt, dt, dt],
        fetch=True
    )
    return rows[0]['session_uuid'] if rows else None


def detect_status_from_sessions(project_name, plan_created):
    """Erkennt den Plan-Status anhand nachfolgender Sessions.

    Logik:
    - Sessions danach am gleichen Projekt mit > 30min Arbeit -> completed
    - Sessions danach mit < 30min -> active (angefangen aber vllt nicht fertig)
    - Keine Sessions danach + aelter als 30 Tage -> archived
    - Sonst -> draft
    """
    if not project_name or not plan_created:
        return 'draft'
    variants = _build_session_name_variants(project_name)
    placeholders = ','.join(['%s'] * len(variants))
    row = execute(
        f"""SELECT
                COUNT(*) as session_count,
                COALESCE(SUM(duration_ms) / 1000 / 60, 0) as total_minutes
            FROM sessions
            WHERE project_name IN ({placeholders})
              AND started_at > %s
              AND started_at < %s + INTERVAL '14 days'""",
        variants + [plan_created, plan_created],
        fetchone=True
    )
    sessions = row['session_count'] if row else 0
    minutes = int(row['total_minutes'] or 0) if row else 0

    if sessions > 0 and minutes >= 30:
        return 'completed'
    if sessions > 0:
        return 'active'

    # Aelter als 30 Tage ohne Sessions -> vermutlich verworfen
    age_row = execute(
        "SELECT EXTRACT(EPOCH FROM (NOW() - %s)) / 86400 as age_days",
        (plan_created,), fetchone=True
    )
    age_days = age_row['age_days'] if age_row else 0
    if age_days > 30:
        return 'archived'

    return 'draft'


def scan_plans():
    """Scannt ~/.claude/plans/ und gibt Liste von Plan-Metadaten zurueck."""
    if not os.path.isdir(PLANS_DIR):
        return []

    plans = []
    for filename in os.listdir(PLANS_DIR):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(PLANS_DIR, filename)
        if not os.path.isfile(filepath):
            continue

        stat = os.stat(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        title = extract_title(content)
        project = detect_project(content)
        category = detect_category(content, title)
        context = extract_context(content)

        plans.append({
            'filename': filename,
            'filepath': filepath,
            'title': title or filename.replace('.md', '').replace('-', ' ').title(),
            'project_name': project,
            'content': content,
            'context_summary': context,
            'category': category,
            'file_hash': file_hash(filepath),
            'file_mtime': stat.st_mtime,
            'created_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        })

    return sorted(plans, key=lambda p: p['file_mtime'], reverse=True)


def sync_plans():
    """Synchronisiert Plans aus dem Dateisystem in die Datenbank."""
    ensure_plans_schema()
    plans = scan_plans()

    stats = {'imported': 0, 'updated': 0, 'unchanged': 0, 'total': len(plans)}

    for plan in plans:
        # Pruefen ob bereits importiert
        existing = execute(
            "SELECT id, file_hash, status FROM project_plans WHERE filename = %s",
            (plan['filename'],),
            fetch=True
        )

        if existing:
            row = existing[0]
            old_id, old_hash = row['id'], row['file_hash']
            if old_hash == plan['file_hash']:
                # Datei unveraendert, aber Status neu berechnen falls noch draft
                if row['status'] == 'draft':
                    new_status = detect_status_from_sessions(
                        plan['project_name'], plan['created_at'])
                    if new_status != 'draft':
                        session_uuid = find_related_session(
                            plan['project_name'], plan['file_mtime'])
                        execute(
                            """UPDATE project_plans
                               SET status = %s,
                                   session_uuid = COALESCE(%s, session_uuid),
                                   updated_at = NOW()
                               WHERE id = %s""",
                            (new_status, session_uuid, old_id)
                        )
                        stats['updated'] += 1
                    else:
                        stats['unchanged'] += 1
                else:
                    stats['unchanged'] += 1
                continue
            # Datei geaendert -> Update (Status beibehalten wenn manuell gesetzt)
            session_uuid = find_related_session(plan['project_name'], plan['file_mtime'])
            execute(
                """UPDATE project_plans
                   SET title = %s, project_name = %s, content = %s,
                       context_summary = %s, category = %s,
                       session_uuid = COALESCE(%s, session_uuid),
                       file_hash = %s, file_mtime = %s, updated_at = NOW()
                   WHERE id = %s""",
                (plan['title'], plan['project_name'], plan['content'],
                 plan['context_summary'], plan['category'],
                 session_uuid,
                 plan['file_hash'], plan['file_mtime'], old_id)
            )
            stats['updated'] += 1
        else:
            # Neu importieren - Status automatisch erkennen
            session_uuid = find_related_session(plan['project_name'], plan['file_mtime'])
            auto_status = detect_status_from_sessions(
                plan['project_name'], plan['created_at'])
            execute(
                """INSERT INTO project_plans
                   (filename, title, project_name, content, context_summary,
                    category, status, session_uuid, file_hash, file_mtime, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (plan['filename'], plan['title'], plan['project_name'],
                 plan['content'], plan['context_summary'], plan['category'],
                 auto_status, session_uuid, plan['file_hash'],
                 plan['file_mtime'], plan['created_at'])
            )
            stats['imported'] += 1

    return stats
