# Full-Project-Recursive-Scanner Recovery Brief (2026-04-17)

## Ziel

Diese Datei dokumentiert den Befund zum mutmaßlich verlorenen
Full-Project-Recursive-Scanner und dient als konkreter Wiederherstellungsauftrag
für Claude Code.

Gemeint ist **nicht** der bestehende Multi-Source-Plan-Scanner
(`services/plan_discovery_service.py`), sondern ein zusätzlicher Scanner, der
nicht nur bekannte Pfade wie `sprints/` oder `plans/` durchsucht, sondern
rekursiv ganze Projektverzeichnisse unter `/mnt/projects/<projekt>/` scannt und
planartige Funde in `project_plans` importiert.

## Kurzfazit

Stand 2026-04-17:

- Der vorhandene Scanner in `services/plan_discovery_service.py` ist **nicht**
  dieser Full-Project-Scanner.
- Er scannt nur feste Quellen und hat explizit `MAX_DEPTH = 3`.
- In Git-Historie, Reflog, `/tmp/project-dashboard-before-recovery.patch`,
  Stash und den sichtbaren Dangling-Commits gibt es **keinen direkt
  rekonstruierbaren Commit** mit einem separaten Full-Project-Recursive-Scanner.
- Wenn der User diesen Scanner am **2026-04-16** mit Codex umgesetzt hat, dann
  ist diese Arbeit sehr wahrscheinlich als **unstaged Workingtree-Arbeit**
  verloren gegangen und wurde nie committet.

## Gesicherte Evidenz

### 1. Der aktuelle Scanner ist bewusst begrenzt

Datei: `services/plan_discovery_service.py`

- Scan-Quellen sind fest kodiert:
  - `~/.claude/plans/`
  - `<project>/sprints/`
  - `<project>/plans/`
  - `<project>/docs/{plans,sprints}/`
  - `<project>/{roadmap,ROADMAP,MASTERPLAN,master-plan}.md`
- `MAX_DEPTH = 3`
- Sprint-Doku sagt explizit:
  `kein rekursiver Full-Tree-Walk`

Das ist der vorhandene Plan-Discovery-Scanner, nicht der verlorene
Full-Project-Scanner.

### 2. `next-session.md` nennt genau diese Lücke

In `next-session.md` steht als offene / unklare Stelle:

- "Zweiter Scanner (Full-Project-Recursive-Walk)"
- User erwähnte einen Sprint-Plan für einen zweiten Scanner, der das gesamte
  Projekt scannt
- kein solcher Sprint-Plan in `sprints/` gefunden
- Status: unklar

Das ist der stärkste textuelle Hinweis darauf, dass eine zusätzliche Arbeit
gemeint war, die nicht im Repo gelandet ist.

### 3. Git-Historie zeigt nur den Multi-Source-Scanner

Gefundene relevante Commits:

- `174424a` Schema: source_path, source_kind, content_hash + plan_scan_exclusions
- `ec339c5` Scanner: plan_discovery_service mit Multi-Source-Discovery
- `9891b05` Import: plans_sync_service + sync_plans delegate
- `a212ec2` API: plan_scan_routes
- `5f5fbce` UI: /plans/scan
- `f1e289d`, `c9de4ca`, `c8374d4` Follow-up / Recovery

Nicht gefunden:

- kein Commit mit `recursive`, `full-project`, `entire project`, `project walk`
- kein neuer Service mit passendem Namen
- kein neuer DB-Pfad für einen zweiten Scanner

### 4. `/tmp/project-dashboard-before-recovery.patch` enthält den Scanner nicht

Der Recovery-Patch in `/tmp/project-dashboard-before-recovery.patch` enthält
große Änderungen an `handoff.md` und Dokumentation, aber keinen erkennbaren
separaten Full-Project-Scanner.

### 5. Stash / Dangling-Commits liefern keinen direkten Treffer

Geprüft wurden:

- `stash@{0}`
- unerreichbare Commits aus `git fsck --full --unreachable`

Befund:

- kein Commit mit eindeutiger Scanner-Implementierung für
  "gesamtes Projekt rekursiv"
- sichtbare Dangling-Stände enthalten nur den bekannten
  `plan_discovery_service.py` mit festen Quellen

## Was vermutlich verloren ging

Sehr wahrscheinlich ging eine lokale, nie committete Arbeit verloren, die
ungefähr Folgendes getan hat:

1. Rekursiver Walk durch `/mnt/projects/<projekt>/...`
2. Erkennung planartiger Markdown-Dateien außerhalb der festen Standardpfade
3. Ableitung von `project_name` weiter aus dem Pfad
4. Import in `project_plans` über die bestehende Upsert-Logik
5. Kennzeichnung in `source_kind`, damit UI / Filter / Recovery nachvollziehen
   können, dass der Fund aus einem Full-Project-Scan stammt

## Wahrscheinlich sinnvoller Zielzustand

Claude Code soll den verlorenen Scanner **als Erweiterung** des bestehenden
Plan-Discovery-Stacks wiederherstellen, nicht als komplett paralleles
Subsystem.

### Architektur-Empfehlung

Bestehende Bausteine wiederverwenden:

- `services/plan_discovery_service.py`
- `services/plans_sync_service.py`
- `services/db_plan_source_schema.py`
- `routes/plan_scan_routes.py`

Bereits vorhandene ähnliche Scan-Logik als Referenz:

- `services/project_scanner.py`
- `services/metadata_extractor.py`

### Empfohlene Umsetzung

#### Option A — bevorzugt

`services/plan_discovery_service.py` erweitern:

- neue Quelle `project_recursive`
- pro Projekt rekursiv scannen, aber mit klaren Guards:
  - harte Blacklist
  - Größenlimit
  - Depth-Limit höher als bisher oder nur für den rekursiven Zweig separat
  - keine `.git`, `node_modules`, `dist`, `build`, `archive`, `backups`
- Funde außerhalb der bisherigen Standardpfade zusätzlich aufnehmen
- `source_kind='project_recursive'`

`services/plans_sync_service.py` erweitern:

- `project_recursive` wie andere Multi-Source-Funde importieren
- Status-/Kategorie-Ableitung sinnvoll festlegen
- vorhandene Upsert-Logik beibehalten

`routes/plans_routes.py` / `static/js/plans.js` anpassen:

- `project_recursive` in `plan_type` / Badge-Mapping berücksichtigen
- Tooltip mit `source_path`

#### Option B — nur falls klarer

Neuen Service `services/project_recursive_plan_discovery.py` anlegen und
danach in `plans_sync_service.scan_all_plans()` zusätzlich mergen.

Option A ist aber konsistenter, weil Discovery bereits zentral existiert.

## Minimale Akzeptanz für Restore

1. Ein Markdown-Plan in einem Projekt-Unterordner außerhalb von
   `sprints/`, `plans/`, `docs/plans`, `docs/sprints` wird gefunden.
2. Der Fund landet nach Sync in `project_plans`.
3. `project_name` wird korrekt aus dem Pfad abgeleitet.
4. `source_kind` ist unterscheidbar von `project_sprints` / `project_plans`.
5. Bestehende Scans werden nicht massiv verlangsamt oder mit False Positives
   geflutet.

## Konkrete Testfälle

Claude Code soll nach dem Restore mindestens diese Fälle prüfen:

1. Datei unter
   `/mnt/projects/project_dashboard/some/subdir/feature-roadmap.md`
   wird gefunden und importiert.
2. Datei unter
   `/mnt/projects/project_dashboard/archive/old-plan.md`
   wird **nicht** importiert.
3. Datei unter
   `/mnt/projects/project_dashboard/node_modules/foo/plan.md`
   wird **nicht** importiert.
4. Bereits importierte Datei wird per `source_path` sauber aktualisiert,
   nicht dupliziert.
5. `/plans` oder `/plans/scan` macht die Quelle des rekursiven Funds sichtbar.

## Restore-Auftrag an Claude Code

Stelle den verlorenen Full-Project-Recursive-Scanner wieder her.

Vorgehen:

1. Behandle den bestehenden `plan_discovery_service.py` als Basis.
2. Implementiere einen zusätzlichen rekursiven Discovery-Pfad für ganze
   Projekte unter `/mnt/projects/<projekt>/`.
3. Nutze die vorhandene Upsert- und Schutzlogik in
   `services/plans_sync_service.py`.
4. Kennzeichne rekursive Funde explizit über `source_kind`.
5. Ergänze die UI-/API-Mappings, damit diese Quelle sichtbar bleibt.
6. Führe keine destruktiven Git-Befehle aus, solange lokale Änderungen
   vorhanden sind.

## Wichtig

Dieser Brief behauptet **nicht**, dass der verlorene Scanner als Commit
rekonstruierbar ist. Der aktuelle Befund ist:

- Feature-Idee klar belegbar
- vorhandener Multi-Source-Scanner klar abgrenzbar
- konkrete verlorene Implementierung im aktuellen Repo **nicht** mehr direkt
  auffindbar

Deshalb ist die Wiederherstellung sehr wahrscheinlich eine
**Neu-Rekonstruktion aus Kontext und Nutzererinnerung**, nicht ein simples
Cherry-Pick.
