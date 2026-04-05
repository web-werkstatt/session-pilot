# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-05
> **Status:** Sprint PX ist im Repo funktional fertig umgesetzt; zusaetzlich ist die Projekt-Discovery fuer `project_dashboard` jetzt als persistente Settings-Option im Dashboard steuerbar, der Plans-Detail-500er auf aelteren DB-Schemas ist serverseitig behoben, Plan-Details koennen jetzt ueber eine eigene Seite mit Tabs statt nur per Modal geoeffnet werden, und Sprint QR ist mit Session 1 bis 4 im UI umgesetzt: `Planning` ist der Projekteinstieg, die Hierarchie `Plan -> Sprint -> Task/Spec` wird im Projekt gerendert, das operative Detailpanel ist angebunden, und Sessions haengen jetzt sichtbar an Marker-, Task-, Spec- und Sprint-Kontexten; ausserdem ist mit Sprint QS jetzt ein separater Architekturpfad fuer die DB-first Ablosung verteilter JSON-Zustandsdaten dokumentiert
> **Naechste Aufgabe:** Den neuen QR-Session-Pfad im Browser gegen echte Projektdaten validieren und danach entscheiden, ob Phase 1 von Sprint QS oder die Reduktion des separaten Session-Tabs als naechster Schritt folgt

---

## Was in dieser Session passiert ist (2026-04-04)

### Sprint QX: Dashboard-Self-Discovery konfigurierbar gemacht

**Ziel:** Das Repo `project_dashboard` nicht mehr hart aus der Projektliste ausschliessen, sondern ueber Settings im Dashboard selbst steuerbar machen.

**Umgesetzt:**
- Neues Persistenz-Layer `services/dashboard_settings_service.py` angelegt
- Settings werden jetzt in `dashboard_settings.json` gespeichert und fallen nur initial auf Env-Defaults zurueck
- Neue API `GET/POST /api/settings/general` angelegt
- `templates/settings.html`, `static/js/settings.js` und `static/css/settings.css` um einen General-Tab mit Toggle fuer `project_dashboard`-Self-Discovery erweitert
- `services/project_scanner.py` und `routes/project_routes.py` lesen die Einstellung jetzt dynamisch aus dem Settings-Service statt aus einer statischen Config-Konstante
- Default bleibt sichtbar; die Option kann jetzt direkt im UI gespeichert werden

**Geaenderte Dateien:**
- `config.py`
- `services/dashboard_settings_service.py`
- `services/project_scanner.py`
- `routes/settings_routes.py`
- `routes/project_routes.py`
- `templates/settings.html`
- `static/js/settings.js`
- `static/css/settings.css`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Im laufenden Dashboard pruefen, dass `project_dashboard` in Listen und Suchtreffern erscheint
- pruefen, ob nach Toggle-Wechsel ein manueller Refresh/Rescan im UI noch klarer gefuehrt werden sollte

### Sprint QY: Plans-Detail gegen Legacy-DB-Schema gehaertet

**Ziel:** Den HTTP-500 beim Oeffnen einer Plan-Card beheben, wenn die produktive DB bereits eine aeltere `specs`-Tabelle ohne neue Strukturspalten besitzt.

**Umgesetzt:**
- Root Cause im Live-Log identifiziert: `GET /api/plans/145` scheiterte in `ensure_plan_structure_schema()` beim Index auf `specs(sprint_plan_id, updated_at DESC)`
- `services/db_service.py` haertet die Schema-Sicherung jetzt ueber `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` fuer `sprint_plans` und `specs`
- Damit funktionieren bestehende Installationen auch dann, wenn `CREATE TABLE IF NOT EXISTS` wegen einer Alt-Tabelle keine neuen Spalten mehr anlegt
- Service neu gestartet und Migration im Live-Kontext erfolgreich ausgefuehrt
- Der zuvor betroffene Endpoint liefert nach dem Fix wieder `200`

**Geaenderte Dateien:**
- `services/db_service.py`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Optional noch Legacy-Constraints/Foreign-Keys fuer `specs` nachziehen, falls spaeter echte Datenintegritaet fuer Altbestandsdaten benoetigt wird

### Sprint QZ: Plan-Detailseite mit Tabs statt Auto-Modal

**Ziel:** Beim Klick auf Plan-Cards eine echte Detailseite bereitstellen, statt die Plans-Seite nur mit `?plan=` zu oeffnen und sofort ein Modal zu zeigen.

**Umgesetzt:**
- Neue Route `GET /plans/<id>` in `routes/plans_routes.py`
- Bestehende Legacy-Links `/plans?plan=<id>` werden serverseitig auf die neue Detailroute umgeleitet
- Neues Template `templates/plan_detail.html` angelegt
- Neue Assets `static/js/plan-detail.js` und `static/css/plan-detail.css` fuer die Detailseite mit Tabs `Overview`, `Content`, `Workflow`, `Handoff`
- Die Detailseite nutzt bestehende APIs `/api/plans/<id>`, `/api/plans/<id>/workflow` und `/api/plans/<id>/handoff`
- Die Projektdetailseite verlinkt Plan-Cards jetzt direkt auf `/plans/<id>`
- Die Plans-Uebersicht navigiert bei Card-Klick jetzt ebenfalls auf die Detailseite statt ein Modal zu oeffnen

**Geaenderte Dateien:**
- `routes/plans_routes.py`
- `templates/plan_detail.html`
- `static/js/plan-detail.js`
- `static/css/plan-detail.css`
- `static/js/plans.js`
- `static/js/project-detail.js`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Im Browser pruefen, ob auf der neuen Detailseite noch Inline-Editing oder weitere Tabs wie `Sections` / `Markers` benoetigt werden

### Sprint QR: Projektzentrierter Planning Workspace geplant

**Ziel:** Die UI fachlich sauber auf die Hierarchie `Project -> Master Plan -> Sprint Plan -> Task/Spec -> Session` ausrichten.

**Umgesetzt:**
- Neuer Sprint-Plan `sprints/sprint-qr-project-planning-workspace.md` angelegt
- Der Plan definiert das Projekt als primaeren Einstieg
- `/plans` wird im Zielbild als globaler Index statt als konkurrierende Arbeitsflaeche beschrieben
- `Planning` im Projekt wird als neue zentrale Hierarchieansicht spezifiziert
- Sessions werden fachlich der operativen Task-/Spec-Ebene untergeordnet
- zusaetzlich sind jetzt Architekturleitplanken dokumentiert: Glossar, Parent-Child-Regeln, Deep-Link-Prinzipien, normierte UI-Begriffe und erlaubte UI-Aktionen pro Ebene
- der Sprint ist jetzt in 5 aufeinander aufbauende Umsetzungs-Sessions heruntergebrochen

**Geaenderte Dateien:**
- `sprints/sprint-qr-project-planning-workspace.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- Den neuen Sprint QR schrittweise in Project-Detail, Plans-Index und Copilot-Navigation umsetzen

## Update 2026-04-05
- Changed: Self-Discovery fuer `project_dashboard` als persistente Settings-Option mit API und UI eingebaut
- Files: `config.py`, `services/dashboard_settings_service.py`, `services/project_scanner.py`, `routes/settings_routes.py`, `routes/project_routes.py`, `templates/settings.html`, `static/js/settings.js`, `static/css/settings.css`
- Verify: `python3 -m py_compile config.py services/dashboard_settings_service.py services/project_scanner.py routes/settings_routes.py routes/project_routes.py` und `node --check static/js/settings.js`
- Next: Im Browser Toggle speichern und pruefen, wie sich Suche, Scan und Refresh direkt verhalten

## Update 2026-04-05
- Changed: Plan-Detail-500 gegen Legacy-DB-Schema behoben, indem `ensure_plan_structure_schema()` fehlende Spalten in `sprint_plans` und `specs` idempotent nachzieht
- Files: `services/db_service.py`
- Verify: `python3 -m py_compile services/db_service.py routes/plans_routes.py`, `sudo python3 -c "from services.db_service import ensure_plan_structure_schema; ensure_plan_structure_schema(); print('ok')"` und `sudo curl http://127.0.0.1:5055/api/plans/145`
- Next: Im Browser denselben Plan erneut oeffnen und auf weitere Legacy-Schema-Abweichungen achten

## Update 2026-04-05
- Changed: Echte Plan-Detailseite mit Tabs gebaut und alte `?plan=`-Links auf `/plans/<id>` umgestellt
- Files: `routes/plans_routes.py`, `templates/plan_detail.html`, `static/js/plan-detail.js`, `static/css/plan-detail.css`, `static/js/plans.js`, `static/js/project-detail.js`
- Verify: `python3 -m py_compile routes/plans_routes.py`, `node --check static/js/plan-detail.js`, `node --check static/js/plans.js`, `node --check static/js/project-detail.js`
- Next: Live im Browser auf Inhalt, Workflow und Handoff-Tabs gegen echte Plaene pruefen

## Update 2026-04-05
- Changed: Neuen Sprint-Plan fuer den projektzentrierten Planning Workspace erstellt
- Files: `sprints/sprint-qr-project-planning-workspace.md`
- Verify: Inhaltlich gegen Zielbild `Project -> Master Plan -> Sprint Plan -> Task/Spec -> Session` geprueft
- Next: Sprint QR operativ in die Projekt-UI ueberfuehren

## Update 2026-04-05
- Changed: Sprint QR um Architekturleitplanken und Navigationsregeln geschaerft
- Files: `sprints/sprint-qr-project-planning-workspace.md`
- Verify: Glossar, Parent-Child-Regeln, Deep-Link-Prinzipien und UI-Aktionsgrenzen sind jetzt explizit dokumentiert
- Next: Bei der Umsetzung alle sichtbaren Begriffe auf `Plan`, `Sprint`, `Spec`, `Task`, `Session` normieren

## Update 2026-04-05
- Changed: Sprint QR in 5 aufeinander aufbauende Umsetzungs-Sessions heruntergebrochen
- Files: `sprints/sprint-qr-project-planning-workspace.md`
- Verify: Jede Session baut jetzt explizit auf der vorherigen auf und hat ein klares Ergebnis
- Next: Umsetzung mit Session 1 beginnen: Navigation und Begriffssystem festziehen

## Update 2026-04-05
- Changed: Sprint QR Session 1 im UI gestartet; Projekt-Tabs und globale Navigation auf `Planning`, `Session History` und `Plan Index` geschoben, `/plans` als read-first Index gerahmt und Plan-Deep-Links mit Ruecksprung in den Projektkontext versehen
- Files: `templates/base.html`, `templates/project_detail.html`, `static/js/project-detail.js`, `templates/plans.html`, `static/js/plans.js`, `templates/plan_detail.html`, `static/js/plan-detail.js`
- Verify: `node --check static/js/project-detail.js`, `node --check static/js/plans.js`, `node --check static/js/plan-detail.js`
- Next: Session 2 umsetzen und im Projekt die echte Hierarchie `Plan -> Sprint -> Task/Spec` statt flacher Plan-Cards rendern

## Update 2026-04-05
- Changed: Sprint QR Session 2 umgesetzt; neuer Read-Endpoint fuer die Projekt-Planning-Hierarchie gebaut und den Projekt-Tab `Planning` von flachen Plan-Cards auf eine sichtbare Hierarchie `Plan -> Sprint -> Spec/Task` umgestellt
- Files: `services/plan_structure_service.py`, `routes/plans_routes.py`, `static/js/project-detail.js`, `static/css/project-detail.css`, `tests/test_plan_structure_service.py`
- Verify: `python3 -m py_compile services/plan_structure_service.py routes/plans_routes.py`, `node --check static/js/project-detail.js`, `pytest tests/test_plan_structure_service.py -q`
- Next: Session 3 umsetzen und fuer `Spec` bzw. `Task` ein operatives Detailpanel mit Ziel, Next Step, Prompt, Checks, Status und Risiko anbinden

## Update 2026-04-05
- Changed: Sprint QR Session 3 umgesetzt; im Projekt-Workspace gibt es jetzt ein selektierbares Detailpanel fuer `Sprint`, `Spec` und operative `Task`-Eintraege, Marker liefern dort Ziel, Next Step, Prompt, Checks und Risiko; zusaetzlich wurde die neue Planning-Logik bewusst in eigene JS/CSS-Assets ausgelagert, damit die 500-Zeilen-Grenze pro Datei eingehalten bleibt
- Files: `services/plan_structure_service.py`, `static/js/project-planning.js`, `static/css/project-planning.css`, `static/js/project-detail.js`, `static/css/project-detail.css`, `templates/project_detail.html`, `tests/test_plan_structure_service.py`
- Verify: `node --check static/js/project-detail.js`, `node --check static/js/project-planning.js`, `pytest tests/test_plan_structure_service.py -q`
- Next: Session 4 umsetzen und echte Sessions ueber `last_session` bzw. Session-Daten sichtbar an Task/Spec haengen

### Sprint PX: Modularer Start der Hashtag-First Markdown-Routine

**Ziel:** Die neue Markdown-first Architektur nicht als Monolith, sondern mit einem wiederverwendbaren Kernservice starten und den ersten produktiven Integrationspfad direkt daran anbinden.

**Umgesetzt:**
- Neuer generischer Service `services/markdown_routine_service.py` angelegt
- Der Service kapselt jetzt Encoding-Fallback, Content-Hash ohne Steuer-Marker, heuristische Markdown-Klassifikation, Tag-Erkennung fuer `#sprint-*`/`#spec-*`, semantische Split-Points und Sprint-/Spec-Struktur-Extraktion
- Die Altdateien unter `upload/hash/` wurden als konkrete Referenz benutzt, aber nicht 1:1 portiert; die Logik wurde auf generische Pattern-Sets und projektuebergreifende Funktionen reduziert
- `services/copilot_marker_service.py` erweitert Marker jetzt um `sprint_tag` und `spec_tag`
- `sprinttomarkers_from_content()` und der bestehende Sprint-Import ziehen bei getaggten Sprint-Dateien Tags direkt aus der neuen Struktur-Extraktion und schreiben sie an Marker
- Marker-Kontext schreibt `sprint_tag` und `spec_tag` jetzt ebenfalls in `marker-context.md`
- Neue Tests fuer den Markdown-Service und die Marker-Tag-Integration laufen lokal gruen: `pytest tests/test_markdown_routine_service.py tests/test_copilot_marker_service.py -q` mit `26 passed`

**Geaenderte Dateien:**
- `services/markdown_routine_service.py`
- `services/copilot_marker_service.py`
- `tests/test_markdown_routine_service.py`
- `tests/test_copilot_marker_service.py`
- `sprints/sprint-px-hashtag-first-markdown-routine.md`

**Naechste Session:**
- `scripts/markdown_tag_migration.py` mit `--check` / `--apply` auf Basis des neuen Services anlegen
- Tag-Setter fuer fehlende `#sprint-*` / `#spec-*` entwerfen
- Marker-Backfill fuer bestehende `handoff.md`-Marker modular auf die neue Struktur-Extraktion setzen
- danach Sprint-/Spec-Parsing und UI-Mapping schrittweise von Titel-Heuristiken auf Tag-Hierarchie umstellen

### Sprint PX: Modul 2 - Check/Apply-Routine fuer fehlende Markdown-Tags

**Ziel:** Den neuen Service sofort operativ machen: fehlende Sprint-/Spec-Tags projektweit erkennen und idempotent direkt in Markdown-Dateien schreiben koennen.

**Umgesetzt:**
- `services/markdown_routine_service.py` um `build_tag_update_plan()` und `apply_tag_update_plan()` erweitert
- Fehlende `#sprint-*`-Tags werden fuer Sprint-Headings und fehlende `#spec-*`-Tags fuer Unterabschnitte innerhalb eines Sprints als Update-Plan vorgeschlagen
- `scripts/markdown_tag_migration.py` neu angelegt
- Das Script unterstuetzt jetzt:
  - `--check` fuer reine Analyse
  - `--apply` fuer idempotentes Schreiben fehlender Tags
  - optional `--project`
  - optional `--handoff` fuer Marker-Pruefung
- Die erste Version schreibt bewusst nur Markdown-Tags; Marker-Backfill bleibt als naechster modularer Schritt separat
- Lokale Tests fuer Tag-Setter, Check/Apply und Marker-Integration laufen gruen: `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py -q` mit `30 passed`

**Geaenderte Dateien:**
- `services/markdown_routine_service.py`
- `scripts/markdown_tag_migration.py`
- `tests/test_markdown_routine_service.py`
- `tests/test_markdown_tag_migration.py`
- `next-session.md`

**Naechste Session:**
- Marker-Backfill fuer bestehende `handoff.md`-Marker in `scripts/markdown_tag_migration.py` bzw. Service-Layer ergaenzen
- Mapping bevorzugt ueber `plan_id`, Sprint-Struktur und Spec-Titel statt loser Volltextsuche
- danach Copilot-/Plan-UI schrittweise auf `Plan -> Sprint -> Spec -> Marker` umstellen

### Sprint PX: Modul 3 - Marker-Backfill fuer bestehende handoff.md Marker

**Ziel:** Bestehende Marker konservativ an die neue Tag-Hierarchie anbinden, ohne freie Volltext-Magie oder blindes Ueberschreiben.

**Umgesetzt:**
- `scripts/markdown_tag_migration.py` baut jetzt einen Struktur-Index aus den gescannten Markdown-Dateien
- Der Marker-Backfill mappt bevorzugt ueber eindeutige `plan_id`
- `spec_tag` wird nur gesetzt, wenn innerhalb des eindeutig gemappten Sprints ein eindeutiger Treffer ueber Task-Titel oder Spec-Titel existiert
- Marker mit bereits gesetztem `sprint_tag` bleiben unangetastet
- `--check` zeigt fuer ungetaggte Marker jetzt vorgeschlagene `sprint_tag`/`spec_tag`-Werte samt Mapping-Grund an
- `--apply` schreibt diese Marker-Felder idempotent in `handoff.md`
- Neue Tests decken Vorschlag, Writeback und zweiten idempotenten Lauf ab; `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py -q` laeuft jetzt mit `32 passed`

**Geaenderte Dateien:**
- `scripts/markdown_tag_migration.py`
- `tests/test_markdown_tag_migration.py`
- `next-session.md`

**Naechste Session:**
- Copilot-/Plan-UI und Parser-Pfade von Titel-Aehnlichkeit auf `sprint_tag`/`spec_tag` umstellen
- bestehende Sprint-Sections- und Source-Mappings gegen getaggte Inhalte pruefen
- optional spaeter Mapping-Heuristiken erweitern, aber nur mit klaren Prioritaetsregeln

### Sprint PX: Modul 4 - Tag-basierter Parser/UI-Pfad fuer Plan Sections

**Ziel:** Den ersten sichtbaren Produktpfad von Frontend-Heuristik auf serverseitige Tag-Hierarchie umstellen.

**Umgesetzt:**
- `services/plan_structure_service.py` nutzt fuer Sprint-/Spec-Struktur jetzt bevorzugt `scan_markdown_structure()` statt nur Heading-RegEx
- `sync_sprint_plans_from_master()` und `sync_specs_from_sprint_plan()` priorisieren `sprint_tag`, `spec_tag` und `plan_id` aus Markdown
- `get_plan_structure()` und `get_sprint_plan_detail()` matchen Marker bevorzugt ueber `sprint_tag` und `spec_tag`, mit Legacy-Fallback auf `plan_id` bzw. bestehende DB-IDs
- Neuer serverseitiger Helper `derive_tagged_plan_sections()` erzeugt direkt die Hierarchie `Plan -> Sprint -> Spec -> Marker`
- `routes/plans_routes.py` liefert in `/api/plans/<id>` jetzt zusaetzlich `tagged_sections`
- `static/js/copilot_board.js` nutzt fuer `Sprint Sections` bevorzugt `plan.tagged_sections` statt die Quellstruktur komplett lokal aus `##`-Headings zu erraten
- Das Board mappt Marker fuer diese Sections jetzt bevorzugt ueber `sprint_tag`; Titel-Aehnlichkeit bleibt nur noch Legacy-Fallback fuer ungetaggte Inhalte
- Das Source-Panel zeigt Tasks jetzt inklusive Spec-Kontext und Marker inkl. Tag-Hierarchie an
- Neue Service-Tests und Syntaxchecks laufen gruen: `pytest tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_copilot_marker_service.py tests/test_plan_structure_service.py -q` mit `34 passed`, plus `node --check static/js/copilot_board.js`

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `routes/plans_routes.py`
- `static/js/copilot_board.js`
- `tests/test_plan_structure_service.py`
- `next-session.md`

**Naechste Session:**
- Das Copilot-Board gegen echte getaggte Plaene im Browser pruefen
- weitere Altpfade auf `sprint_tag` / `spec_tag` umziehen, insbesondere dort, wo noch numerische `sprint_plan_id` / `spec_id` als Hauptpfad dienen
- optional API-Responses fuer Marker- und Plan-Detailansichten noch expliziter um Hierarchie-Metadaten erweitern

### Sprint PX: Abschlussstand im Repo

**Ziel:** Die restlichen naheliegenden Legacy-Pfade im Code schliessen, damit ausser Live-Validierung keine groessere Sprint-Arbeit mehr offen bleibt.

**Umgesetzt:**
- `services/plan_structure_service.py` priorisiert bei DB-Referenzaufloesung fuer Specs jetzt `spec_tag` vor `spec_title`
- `services/copilot_marker_service.py` reicht `spec_tag` in die Struktur-Referenzaufloesung durch
- `services/copilot_service.py` fuehrt `sprint_tag` und `spec_tag` jetzt explizit im kompakten Marker-Kontext fuer Copilot-Calls mit
- Tests fuer diese Restpfade ergaenzt; die relevanten Sprint-Pfade laufen lokal mit `75 passed`
- Python-Syntaxcheck und `node --check static/js/copilot_board.js` laufen ebenfalls gruen

**Geaenderte Dateien:**
- `services/plan_structure_service.py`
- `services/copilot_marker_service.py`
- `services/copilot_service.py`
- `tests/test_plan_structure_service.py`
- `tests/test_copilot.py`
- `next-session.md`
- `sprints/sprint-px-hashtag-first-markdown-routine.md`

**Naechste Session:**
- echte getaggte Plaene im Browser pruefen
- nur noch reale Mapping-Abweichungen nachschaerfen, falls sie in Live-Daten auftauchen

### Neuer Gesamt-Sprint-Plan fuer Hashtag-First Markdown-Routine

**Ziel:** Die fachliche Kette `Plan -> Sprint -> Spec -> Marker` als Markdown-first und projektuebergreifend planbar machen, inklusive Wiederverwendung der alten Hash-/Parser-Logik aus IR-Tours.

**Umgesetzt:**
- Neue Sprint-Datei `sprints/sprint-px-hashtag-first-markdown-routine.md` angelegt
- Der Plan definiert `#sprint-*` und `#spec-*` als stabile Tags fuer Sprint und Spec
- Marker sollen kuenftig `sprint_tag` und optional `spec_tag` tragen
- Der Plan ersetzt die DB-first-Richtung als primaere Architektur und beschreibt stattdessen eine generische Python-Routine fuer alte und neue Projekte
- Als Altquellen fuer die neue Routine sind `hash_manager.py`, `md_classifier.py` und `split_fragenkatalog_v4_safe.py` aus `proj_irtours/archive/ALT/tools/scripts` festgehalten
- Der Plan enthaelt jetzt explizit eine projektuebergreifende Tag-Migration mit `--check`/`--apply`, Tag-Setter fuer Sprint/Spec und einen Marker-Updater fuer `handoff.md`

**Geaenderte Dateien:**
- `sprints/sprint-px-hashtag-first-markdown-routine.md`
- `next-session.md`
- `sprints/master-plan-2026-04-01.md`

**Naechste Session:**
- `services/markdown_routine_service.py` als generischen Parser-/Klassifikations-Service anlegen
- `scripts/markdown_tag_migration.py` fuer projektweiten `check/apply`-Lauf entwerfen
- Marker-Schema um `sprint_tag/spec_tag` erweitern
- Sprint-/Spec-Parsing und UI-Mapping schrittweise auf Tags umstellen

### Copilot Sprint P-E3: Execution-Rating & Feedback fuer Marker

**Ziel:** Nach markerbezogenen Sessions eine leichte manuelle Ausfuehrungsbewertung erfassen, die am Marker und optional an der Session haengt.

**Umgesetzt:**
- `services/copilot_marker_service.py` um optionale Marker-Felder `execution_score`, `execution_comment`, `last_execution_at` erweitert; `update_execution_rating()` validiert `0..5`, schreibt die Marker-Felder und aktualisiert bei Bedarf auch `sessions.execution_score` / `sessions.execution_comment`
- `services/db_service.py` erweitert `ensure_session_review_schema()` idempotent um die neuen Session-Spalten fuer Execution-Ratings
- `routes/copilot_routes.py` enthaelt jetzt `GET/POST /api/marker/<marker_id>/execution-rating`
- `routes/session_routes.py` liefert in `/api/sessions/<uuid>` zusaetzlich `session.marker`, wenn ein Marker denselben `last_session`-Wert traegt
- `templates/session_detail.html`, `static/js/session-detail.js` und `static/css/session-detail.css` haben ein kleines Rating-Panel fuer den zugeordneten Marker; Speichern sendet den Score zusammen mit `sessionid`
- `templates/copilot_board.html`, `static/js/copilot_board.js` und `static/css/copilot.css` zeigen Execution-Score und Kommentar direkt im Board bzw. Marker-Panel an und erlauben dort schnelles Ueberschreiben
- Tests decken Marker-Rating, Session-Update und den API-Flow ab; `pytest tests/test_copilot_marker_service.py tests/test_copilot.py -q` laeuft lokal mit `55 passed`

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/db_service.py`
- `routes/copilot_routes.py`
- `routes/session_routes.py`
- `templates/copilot_board.html`
- `templates/session_detail.html`
- `static/js/copilot_board.js`
- `static/js/session-detail.js`
- `static/css/copilot.css`
- `static/css/session-detail.css`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`

**Naechste Session:**
- Den Flow einmal mit einer echten Session pruefen, bei der `last_session` auf einen Marker zurueckgeschrieben wurde
- P-E4 kann auf Basis der neuen Marker-/Session-Felder Monitoring und Vergleiche aufbauen

### Copilot Sprint P5: Sprint->Marker Fallback fuer DB-Plan-Content

**Ziel:** Der Button `Sprint -> Marker` soll nicht nur mit einer separaten Sprint-Datei funktionieren, sondern auch dann, wenn der aktuelle Plan bereits als `project_plans.content` vorliegt.

**Umgesetzt:**
- `static/js/copilot_board.js` schickt fuer den Import jetzt nur noch `filename` bzw. die semantische Plan-ID statt eines hart verdrahteten `upload/Sprints/...`-Pfads
- `routes/copilot_routes.py` faellt in `POST /api/sprint/<plan_id>/to-markers` bei `sprint_missing` auf den DB-Planinhalt (`project_plans.content`) zurueck
- `services/copilot_marker_service.py` enthaelt dafuer jetzt `sprinttomarkers_from_content()`
- Tests decken den Fallback-Flow ohne externe Sprint-Datei ab; `pytest tests/test_copilot_marker_service.py tests/test_copilot.py -q` laeuft mit `57 passed`

**Naechste Session:**
- Im Live-Board einmal den Button `Sprint -> Marker` gegen einen echten DB-Plan ohne separate Sprint-Datei pruefen

### Copilot Board: Sprint Sections ueber dem Marker-Board

**Ziel:** Die Quelle `Plan/Sprint -> Marker` dauerhaft sichtbar machen statt nur ueber einen Import-Button.

**Umgesetzt:**
- `templates/copilot_board.html`, `static/js/copilot_board.js` und `static/css/copilot.css` zeigen jetzt oberhalb des Marker-Boards einen `Sprint Sections`-Bereich
- Die Cards werden direkt aus `project_plans.content` ueber `##`-Abschnitte abgeleitet und gegen vorhandene Marker gemappt
- Jede Section-Card zeigt Abschnittstitel, Kurzsummary, Task-Anzahl, Mapping-Status und die ersten zugeordneten Marker
- Das rechte Panel hat zusaetzlich einen `Source`-Tab mit Abschnitt, erkannten Tasks, zugeordneten Markern und Rohinhalt
- JS-Syntaxcheck und Copilot-Tests laufen lokal weiter gruen: `node --check static/js/copilot_board.js`, `pytest tests/test_copilot.py tests/test_copilot_marker_service.py -q`

**Naechste Session:**
- Live im Browser pruefen, ob die Section-Erkennung fuer verschiedene Planformate fein genug ist oder noch mehr Heading-/Task-Heuristiken braucht

### Copilot Sprint P4: Session Write-back geschlossen

**Ziel:** Den Session-Ende-Stand explizit in den zugehoerigen Marker in `handoff.md` zurueckschreiben, ohne neue Auto-Start-Logik einzufuehren.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `close_marker()` erweitert; schreibt gezielt `status`, `naechster_schritt`, `last_session` und `updated_at` in den betroffenen Marker zurueck
- `routes/copilot_routes.py` um `POST /api/copilot/markers/<id>/close` erweitert; liefert definierte Fehler fuer `handoff_missing` und `marker_not_found` und kann `project_id` bei Bedarf aus `marker-context.md` ableiten
- `marker-context.md` enthaelt beim Aktivieren jetzt zusaetzlich `project_id`, damit die Session-Zuordnung stabiler bleibt und der Close-Flow ohne explizites `project_id` arbeiten kann
- `static/js/copilot_board.js` hat eine kleine `closeMarkerSession()`-Hilfsfunktion; nach erfolgreichem Close wird das Board neu geladen und zeigt den Statuswechsel spaetestens beim Refresh
- Tests decken den Service-Roundtrip und den neuen Close-Endpunkt ab; ein manueller Test-Flow `activate -> close -> parse_markers()` liefert `done`, `last_session` und aktualisierten Next Step
- `tests/test_copilot.py` laeuft jetzt lokal ohne Postgres: In-Memory-Copilot-DB-Fake in `tests/conftest.py`, Redirect-Erwartung fuer `/copilot` aktualisiert und Bild-Persistenz im Copilot-Service an die bestehende API-Spec angeglichen
- Copilot-/Plan-Testinfrastruktur teilweise vereinheitlicht: `tests/test_copilot.py`, `tests/test_plan_sections.py` und der Copilot-Binding-Test in `tests/test_plan_workflow.py` nutzen jetzt denselben Mock-/Shared-Fixture-Pfad; reine UI-Render-Tests erzeugen keinen DB-Plan mehr
- `tests/test_plan_workflow.py` Handoff-Drift behoben: Legacy-Import auf den aktuellen `project_handoff_service` umgestellt, Erwartungen auf das Marker-Format aktualisiert und Handoff-Tests mit kleinem In-Memory-Plan-Store von Postgres entkoppelt

### Copilot Sprint P5: Sprint -> Marker Import

**Ziel:** Aufgaben aus einem Sprint-Plan per Klick in Marker in `handoff.md` ueberfuehren, ohne Duplikate zu erzeugen.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `sprinttomarkers()` und `buildsuggestion()` erweitert; Sprint-Sektion wird ueber `Plan-ID` gelesen, Aufgaben-Bullets werden als Marker geschrieben oder aktualisiert
- Marker-IDs sind deterministisch aus `plan_id + titel`, so dass wiederholte Aufrufe keine doppelten Marker erzeugen
- `routes/copilot_routes.py` enthaelt jetzt `POST /api/sprint/<plan_id>/to-markers`
- `templates/copilot_board.html` und `static/js/copilot_board.js` haben den Button `Sprint -> Marker`; nach erfolgreichem Import wird das Marker-Board neu geladen
- Das Board erkennt fuer Marker bei Bedarf eine semantische `Plan-ID` aus dem Plan-Inhalt und faellt sonst auf die bisherige numerische Plan-ID zurueck
- `static/css/copilot.css` zeigt Marker-Titel jetzt ueber bis zu vier Zeilen und den Vorschau-/Prompt-Text ueber bis zu drei Zeilen statt nur als Einzeiler; ausserdem sind die Board-Spalten fuer Marker-Cards breiter, damit TODO/GENERATING/DONE/BLOCKED mehr Inhalt aufnehmen
- `static/js/copilot_board.js` rendert den Vorschau-Block direkt unter dem Marker-Titel statt erst unter Gate/Status-Hinweisen, damit der eigentliche Inhalt in der Card frueher lesbar ist
- `static/css/copilot.css` haertet die Chat-Nachrichten im rechten Panel gegen Overflow ab; lange Antworten, Markdown-Code und Tabellen umbrechen bzw. bleiben innerhalb der Chat-Card
- `static/css/copilot.css` haertet die Scroll-Container im rechten Chat-Panel mit `min-height: 0` ab, damit Chat-Boxen beim Scrollen nicht abgeschnitten werden
- `services/copilot_service.py` persistiert fuer `copilot_runs` jetzt auch `input_tokens`, `output_tokens`, `total_tokens` und `cost_usd`; `static/js/copilot_board.js` zeigt diese API-Kosten als Meta-Zeile unter Assistant-Nachrichten im Chat-Panel an
- `services/copilot_service.py` baut vor dem Perplexity-Call jetzt serverseitig einen kompakten Marker-Kontext aus `marker-context.md` und `handoff.md`; `handoff.md` bleibt fuehrende Wahrheit, Frontend-Kontext ist nur noch Fallback
- `services/copilot_service.py` loest fuer den serverseitigen Marker-Kontext jetzt auch den lesbaren `plan_title` aus `project_plans` auf; `static/js/copilot_board.js`, `static/js/plans.js` und `templates/copilot_landing.html` zeigen bzw. verwenden den Plan-Namen in Panel und Copilot-URL zusaetzlich zur `plan_id`

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `routes/copilot_routes.py`
- `templates/copilot_board.html`
- `static/js/copilot_board.js`
- `static/css/copilot.css`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`

**Naechste Session:**
- Den Import einmal gegen reale Sprint-Dateien im laufenden Board pruefen
- Optional spaeter die Sprint-Pfad-Ableitung weiter haerten, falls Plans aus anderen Verzeichnissen kommen

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/copilot_service.py`
- `routes/copilot_routes.py`
- `static/js/copilot_board.js`
- `tests/conftest.py`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `tests/test_plan_sections.py`
- `tests/test_plan_workflow.py`

**Naechste Session:**
- Optional den Close-Endpunkt aus einer Session-Detailansicht oder einem Import-Flow explizit aufrufen
- Copilot-Workspace weiter optisch nachschaerfen; P4 selbst fuehrt keine neue Session-Start-Logik ein

---

## Was in dieser Session passiert ist (2026-04-03)

### Session-Abschluss: Live-Stand konsolidiert

**Ziel:** Den aktuellen Produktstand fuer die naechste Session realistisch zusammenfassen.

**Stand jetzt:**
- Sidebar ist task-basiert gruppiert, verdichtet, responsiv und mit Accordions fuer seltenere Bereiche live
- Copilot Sprint P3 ist live: Marker-Aktivierung schreibt `marker-context.md`, setzt Marker auf `in_progress`, startet aber keine Session automatisch
- `Quality` und `Governance` zeigen nur noch Projekte mit relevanten Datei-Aenderungen in den letzten 90 Tagen
- Mehrere UI-/Service-Fixes der Session sind bereits auf `main` gepusht und auf dem Server deployed

**Naechster sinnvoller Fokus:**
- Copilot-Workspace visuell und funktional fertigziehen, statt weitere globale Navigation umzubauen

### Responsive Sidebar fuer Mobile

**Ziel:** Die linke Navigationsleiste soll auf Tablet/Mobile nicht mehr fix den Content einengen, sondern als sauberer Drawer funktionieren.

**Umgesetzt:**
- `templates/base.html` um einen Sidebar-Backdrop erweitert
- `static/js/base.js` um Mobile-Drawer-Logik, `Esc`-Close, Focus-Restore und Auto-Close bei Navigation erweitert
- `static/css/layout.css` fuer Off-Canvas-Sidebar, Backdrop und responsive Topbar angepasst
- `static/css/base.css` sperrt Body-Scroll, solange die mobile Sidebar offen ist
- Auf Mobile scrollt jetzt die gesamte Sidebar inklusive `Help Center` und `Settings`, statt den Footer separat stehen zu lassen

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `static/css/layout.css`
- `static/css/base.css`

### Sidebar-Navigation logisch gestrafft

**Ziel:** Die globale Navigation soll weniger verstreut wirken und in der Reihenfolge schneller erfassbar sein.

**Umgesetzt:**
- `templates/base.html` gruppiert die Sidebar jetzt in `Core`, `AI Ops`, `Engineering` und `Content`
- `Plans`, `Copilot` und `New Project` sind in den Kernbereich gezogen
- Lange Labels wurden gekuerzt, z.B. `Claude Sessions` -> `Sessions`, `Model Comparison` -> `Models`, `LLM Commands` -> `Commands`

**Geaenderte Dateien:**
- `templates/base.html`

### Sidebar visuell verdichtet

**Ziel:** Die linke Navigation soll auf Desktop weniger schwer und gross wirken, ohne an Lesbarkeit zu verlieren.

**Umgesetzt:**
- `static/css/layout.css` auf dichtere Sidebar-Typografie und flachere Nav-Zeilen umgestellt
- Section-Labels feiner und ruhiger gemacht
- Active-/Hover-State weniger breit und eher als kompakte Surface statt als schwere Vollflaeche umgesetzt
- Footer-Links visuell als Utility-Layer abgeschwaecht

**Geaenderte Dateien:**
- `static/css/layout.css`

### Sidebar auf Task-Mentalmodell umgestellt

**Ziel:** Die globale Navigation soll sich an echten Nutzeraufgaben statt an internen Systemkategorien orientieren.

**Umgesetzt:**
- `templates/base.html` gruppiert die Sidebar jetzt in `Arbeiten`, `Auswerten`, `System`, `Inhalte`, `Integrationen`
- `Copilot`, `Dashboard` und `Sessions` sind als primaere Ziele hervorgehoben
- `System` ist als einklappbarer Block umgesetzt und standardmaessig reduziert
- `External` wurde zu `Integrationen` umbenannt
- `static/js/base.js` speichert den Collapse-Zustand des `System`-Blocks in `localStorage`
- `static/css/layout.css` staerkt Section-Header und gibt `Copilot` einen klareren Fokuszustand

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`
- `static/css/layout.css`

### Startseite nur noch als ein Sidebar-Ziel

**Ziel:** `/` soll in der Navigation nicht mehr doppelt als `Dashboard` und `Projects` auftauchen.

**Umgesetzt:**
- `templates/base.html` fuehrt die Startseite jetzt nur noch als `Projects`
- der aktive Zustand greift fuer `dashboard` und `projects` auf demselben Sidebar-Eintrag
- der separate `Dashboard`-Eintrag ist entfernt

**Geaenderte Dateien:**
- `templates/base.html`

### Models nach Auswerten verschoben

**Ziel:** `Models` soll fachlich als Analyse-/Vergleichsbereich statt als Systempunkt eingeordnet sein.

**Umgesetzt:**
- `templates/base.html` verschiebt `Models` aus `System` nach `Auswerten`
- der `System`-Block bleibt dadurch klarer auf operative und infrastrukturelle Punkte fokussiert

**Geaenderte Dateien:**
- `templates/base.html`

### Seitenaktionen vor globalem Hilfe-Icon

**Ziel:** Kontextbezogene Header-Aktionen wie `Guide` sollen vor dem globalen Hilfe-Icon stehen.

**Umgesetzt:**
- `templates/base.html` rendert `topbar_actions` jetzt vor dem globalen `?`-Hilfe-Icon
- auf `/quality` steht der `Guide`-Button damit vor dem Help-Center-Shortcut

**Geaenderte Dateien:**
- `templates/base.html`

### Quality/Governance/Audits/Commands als eigener Block

**Ziel:** Bewertungs- und Steuerungsfunktionen sollen nicht im Infrastruktur-Block `System` untergehen.

**Umgesetzt:**
- `templates/base.html` fuehrt jetzt einen eigenen Bereich `Steuern`
- `Quality`, `Governance`, `Audits` und `Commands` liegen nicht mehr unter `System`
- `System` bleibt damit auf operative Themen wie `Containers`, `Dependencies` und `Schedules` fokussiert

**Geaenderte Dateien:**
- `templates/base.html`

### Governance nur fuer kuerzlich geaenderte Projekte

**Ziel:** Die Governance-Uebersicht soll wie `Quality` nur aktive Projekte zeigen, die in den letzten 90 Tagen relevante Datei-Aenderungen hatten.

**Umgesetzt:**
- `services/governance_service.py` filtert `get_governance_overview()` jetzt auf Projektdateien mit relevanter Aenderung in den letzten 90 Tagen
- `project.json` allein zaehlt bewusst nicht als Aktivitaet, damit keine reinen Metadaten-Leichen in `/governance` erscheinen
- Tests decken den Fall "recent code" sowie "nur frisches project.json, aber alter Code" explizit ab

**Geaenderte Dateien:**
- `services/governance_service.py`
- `tests/test_governance_gate.py`

### Inhalte und Integrationen als Accordion

**Ziel:** Seltenere Sidebar-Bereiche sollen Platz sparen und dieselbe Collapse-Logik wie `System` nutzen.

**Umgesetzt:**
- `templates/base.html` fuehrt `Inhalte` und `Integrationen` jetzt als einklappbare Sidebar-Bloecke
- `static/js/base.js` speichert deren Collapse-Zustand ebenfalls in `localStorage`
- beide Bereiche starten standardmaessig eingeklappt

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`

### Auswerten als Accordion hinter Steuern

**Ziel:** `Auswerten` soll dieselbe Accordion-Logik wie `System`, `Inhalte` und `Integrationen` nutzen und in der Reihenfolge hinter `Steuern` stehen.

**Umgesetzt:**
- `templates/base.html` fuehrt `Auswerten` jetzt als einklappbaren Block
- `Auswerten` steht jetzt nach `Steuern`
- `static/js/base.js` erweitert die Default-Collapse-Zustaende um `analysis`

**Geaenderte Dateien:**
- `templates/base.html`
- `static/js/base.js`

### Handoff-Fallback fuer neue Projektordner

**Ziel:** `handoff.md` auch dann robust erzeugen, wenn ein Projektordner schon existiert, aber in `project_plans` noch keine Plaene vorhanden sind.

**Umgesetzt:**
- `services/project_handoff_service.py` erzeugt in `write_handoff()` jetzt einen minimalen `copilot_markers_v1`-Handoff statt mit `None` abzubrechen
- Neuer Minimal-Handoff bleibt marker-kompatibel, enthaelt aber bewusst keine Marker-Bloecke
- Tests decken jetzt den Fall "Projektordner existiert, aber keine Plans" explizit ab

**Geaenderte Dateien:**
- `services/project_handoff_service.py`
- `tests/test_project_handoff.py`

### Copilot Chat-Verlauf fuer Marker wiederhergestellt

**Ziel:** Panel-Chat im Copilot-Board soll Marker-Threads wieder laden koennen, ohne auf `/api/copilot/runs` mit 500 zu scheitern.

**Umgesetzt:**
- `services/copilot_service.py` akzeptiert in `list_copilot_runs()` jetzt wieder `plan_id` als Filter
- Verlauf-Response liefert `plan_id` wieder mit aus
- Damit funktioniert der Marker-Chat-Load aus `static/js/copilot_board.js` wieder gegen den Live-Endpunkt

**Geaenderte Dateien:**
- `services/copilot_service.py`

### Copilot Workspace Redesign (teilweise umgesetzt)

**Ziel:** /copilot?plan_id=X als AI-native Work OS umbauen (Referenzbild vorhanden).

**Umgesetzt:**
- `/copilot` ohne plan_id → Redirect zum letzten aktiven Plan (oder /plans)
- Landing-Page wird umgangen (kein doppeltes Plan-Dashboard mehr)
- Workspace Header mit Plan-Switcher Dropdown
- Progress-Bar (done/total, Prozent, Task/Done/Review Counts)
- Board-Spalten: Backlog, Ready, Generating (statt in_progress), Review, Done, Blocked
- Emoji-Icons, Beschreibungszeilen, Empty-States pro Spalte
- Cards: Typ-Badge, Message-Count, Generating-Indikator, Zeitinfo, Hover-Actions
- Detail-Panel rechts: oeffnet/schliesst bei Karte-Klick, Tabs (Chat/Output/History)
- Panel-Close gibt Board volle Breite zurueck
- Lila-Farbe entfernt, Landing-Page auf var(--accent) umgestellt
- shadcn/ui Zinc-Palette als CSS-Design-Tokens eingefuehrt

**Geaenderte Dateien:**
- `routes/copilot_routes.py` — Redirect-Logik (redirect import, /copilot Fallback)
- `templates/copilot_board.html` — Komplett neu: Header, Progress, Split-View, Panel mit Tabs
- `templates/copilot_landing.html` — Lila entfernt, Zentrierung entfernt (wird nicht mehr direkt aufgerufen)
- `static/css/copilot.css` — Komplett neu: shadcn/ui Zinc-Tokens, alle Komponenten
- `static/css/copilot_landing.css` — Lila-Farbwerte durch var(--accent) ersetzt
- `static/js/copilot_board.js` — Komplett neu: Generating-Column, Progress, Plan-Switcher, Tabs, Panel-Logik

**Bekannte Probleme / User-Feedback:**
- Qualitaet entspricht NICHT dem Referenzbild (Linear/Vercel-Niveau nicht erreicht)
- Zu viele Iterationen fuer selbst eingefuehrte Bugs (Panel-Close, Farben, Icons)
- Zeitanzeige in Cards bricht auf 3 Zeilen um ("24 min ago" → 3 Zeilen)
- shadcn-Tokens kollidieren teilweise mit base.html Design-System
- Output-Tab und History-Tab sind leer (nur Empty-States)
- User ist enttaeuscht vom Ergebnis

### Copilot Design-System Refresh (gezielte Nachschaerfung)

**Ziel:** Kein weiterer Komplettumbau, sondern ein kleines, sauberes Dark-SaaS-Design-System auf bestehender Struktur.

**Umgesetzt:**
- Zentrale Dark-SaaS-Tokens in `static/css/design-tokens.css` auf konsistente Werte vereinheitlicht
- Neue Basis-Klassen in `static/css/components.css`: `ui-card`, `ui-panel`, `ui-button`, `ui-badge`, `ui-tabs`, `ui-input`
- Board-Card-Pattern im Copilot-Board auf die neuen Primitives gezogen (`ui-card`, `ui-badge`, `ui-button`)
- Rechtes Detail-Panel auf `ui-panel` plus neue Tabs-/Input-Primitive umgestellt
- Keine neue Seite, keine Frameworks, keine Backend- oder Architektur-Aenderung

**Geaenderte Dateien:**
- `static/css/design-tokens.css`
- `static/css/components.css`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `templates/copilot_board.html`

**Offen / naechster sinnvoller Schritt:**
- Im Browser pruefen, ob das Panel visuell sauber mit bestehendem `base.html` harmoniert
- Bei Bedarf als naechsten kleinen Schritt weitere Copilot-Elemente selektiv auf `ui-*` Klassen umstellen

### Copilot Header + Progress Refactor

**Ziel:** Nur den oberen Workspace-Bereich hochwertiger machen, ohne Board, Cards oder Panel weiter anzufassen.

**Umgesetzt:**
- Workspace-Header als eigener `ui-panel` Block mit klarer Hierarchie aufgebaut
- Linke Seite trennt jetzt Brand, Plan-Switcher und aktiven Plan
- Rechte Actions (`AI Task`, `Ask Copilot`) aus der engen Topbar in den Workspace-Header verschoben
- Progress-Leiste als kompakter Info-Block mit staerkerer visueller Gewichtung umgesetzt
- Stats (`Tasks`, `Done`, `Review`) als kleine `ui-card` KPI-Elemente dargestellt
- Bestehende Logik fuer Plan-Laden, Switcher und Progress-Berechnung unveraendert gelassen

**Geaenderte Dateien:**
- `templates/copilot_board.html`
- `static/css/copilot.css`
- `static/js/copilot_board.js`

### Marker-/Zeiger-Orchestrierung geplant

**Ziel:** Copilot fachlich von einem reinen Section-Board zu einem Markdown-gefuehrten Marker-Workflow weiterdenken.

**Erarbeitet:**
- `handoff.md` gegen aktuelle Copilot-UI geprueft: passt fachlich nicht, weil `handoff.md` projektweit aggregiert ist, Copilot-Cards aber plan-spezifisch sind
- Neue Detail-Planung erstellt: `sprints/sprint-17-marker-driven-copilot-orchestration.md`
- Master-Plan um Verweis auf Sprint 17 erweitert

**Kernidee Sprint 17:**
- feste Markdown-Datei als fuehrender Projektzustand
- Marker/Zeiger darin als adressierbare Arbeitseinheiten
- Anzeige der Marker als Copilot-Cards
- Card-Klick -> Chat/Perplexity fuer genau diesen Marker-Kontext
- spaeterer Status-Write-Back in dieselbe Datei

### Sprint P1 umgesetzt: Marker-Schema & handoff.md Generator

**Ziel:** `handoff.md` von einer aggregierten Textdatei auf ein maschinenlesbares Marker-Dual-Format umstellen.

**Umgesetzt:**
- `services/copilot_marker_service.py` neu: `Marker`-Dataclass, `_serialize_marker()`, `_write_marker()`, `parse_markers()`
- Wahrheitsquelle beim Einlesen ist jetzt der JSON-Block im HTML-Kommentar; Markdown-Teil wird immer neu aus dem Objekt erzeugt
- `services/project_handoff_service.py` schreibt jetzt Marker-Bloecke statt aggregiertem Prosatext
- Gezielte Tests fuer Parser/Writer-Roundtrip und Generator erstellt

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/project_handoff_service.py`
- `tests/test_copilot_marker_service.py`
- `tests/test_project_handoff.py`

### Sprint P2 umgesetzt: Cards aus Markdown + Status Write-back

**Ziel:** Copilot-Board auf Marker aus `handoff.md` umstellen und Status-/Prompt-Write-back direkt in die Datei schreiben.

**Umgesetzt:**
- `services/copilot_marker_service.py` um Marker-Read-/Update-Funktionen erweitert: `list_markers_for_plan()`, `get_marker_context()`, `update_marker_status()`, `update_marker_fields()`
- `routes/copilot_routes.py` um Marker-API erweitert: `GET /api/copilot/markers`, `GET /api/copilot/markers/<id>`, `PATCH /status`, `PATCH /fields`
- `static/js/copilot_board.js` laedt Board-Cards jetzt aus der Marker-API statt aus `plan_sections`
- Drag & Drop schreibt Marker-Status direkt nach `handoff.md` zurueck
- Gate-Logik im Board sichtbar gemacht (`is_activatable`, `gate_reason`)
- Detail-Panel zeigt Marker-Felder und bietet `Vorschlag uebernehmen` fuer `prompt_suggestion -> prompt`
- Chat im Panel auf markerbasierte Copilot-Threads via `thread_id=marker:<plan_id>:<marker_id>` umgelegt
- `services/project_handoff_service.py` erzeugt Default-Checks, damit Prompt-Uebernahme Marker sinnvoll aktivierbar machen kann
- Gezielte Marker-/API-Tests fuer P2 ergaenzt

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `services/project_handoff_service.py`
- `routes/copilot_routes.py`
- `templates/copilot_board.html`
- `static/css/copilot.css`
- `static/js/copilot_board.js`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`

### Sprint P3 umgesetzt: Prompt-Chain & Execution

**Ziel:** Aktivierbare Marker direkt aus dem Copilot-Board in einen fokussierten Ausfuehrungskontext ueberfuehren, ohne Sessions automatisch zu starten.

**Umgesetzt:**
- `services/copilot_marker_service.py` um `is_activatable()` und `activate_marker()` erweitert; die Aktivierung nutzt dieselbe Gate-Logik wie P2, schreibt `marker-context.md` fuer genau einen Marker und setzt den Marker in `handoff.md` auf `in_progress`
- Neue API `POST /api/copilot/markers/<id>/activate` in `routes/copilot_routes.py` liefert bei Erfolg `{ ok: true, status: "in_progress" }` und bei Gate-Block sauber `{ ok: false, error: "gate_blocked", reason: ... }`
- `static/js/copilot_board.js` zeigt pro freigegebener Card einen `OK`-Button, ruft die Aktivierung auf und aktualisiert Status/UI lokal ohne Session-Autostart
- `CLAUDE.md` minimal um die Regel erweitert, dass `marker-context.md` als aktueller Fokusauftrag gilt
- Tests fuer Service- und API-Roundtrip der Marker-Aktivierung ergaenzt

**Geaenderte Dateien:**
- `services/copilot_marker_service.py`
- `routes/copilot_routes.py`
- `static/js/copilot_board.js`
- `tests/test_copilot_marker_service.py`
- `tests/test_copilot.py`
- `CLAUDE.md`

### Testdaten angelegt
- 5 Sections in Plan #5 erstellt (IDs 796-800)
- Verschiedene Status: backlog, ready, in_progress, review, done
- Diese koennen geloescht werden wenn nicht gewuenscht

### Copilot Landing-Page Aenderungen (vor dem Redesign)
- Lila Gradient-Farbe durch var(--accent) blau ersetzt
- Zentrierung entfernt (Karten linksbuendig)
- continue-card, quickstart-btn Farben angepasst

---

## Naechste Session
- Live-Validierung des modularisierten Copilot-Flows gegen echte Plaene: Plan-Switcher, `Sprint -> Marker`, Panel-Tabs, Execution-Rating, Marker-Aktivierung, Close-/Write-back
- Die neue QR-Session-Historie im Projekt-Planning gegen echte Daten pruefen: Marker, gleichnamige Markdown-Tasks, Spec-Aggregation, Session-Detail-Link
- Alternativ oder direkt danach Phase 1 von Sprint QS beginnen: DB-Zielstruktur fuer `notifications`, `favorites`, `relations`, `ideas` und `dashboard_settings` anlegen und Root-JSON-Stores schrittweise DB-first machen
- Optional danach den separaten Projekt-Tab `Session History` im Sinne von Sprint QR weiter reduzieren oder sekundarer rahmen

## Kontext
- letzter Feature-Commit: `bbaf112` `Feature: modularize copilot markdown workflow and session detail`
- letzter Doku-Commit: `372720d` `Dokumentation: update sprint commit hashes`
- `origin/main` ist aktuell, `project-dashboard` lief beim Abschluss sauber

## Lokal offen
- `handoff.md`
- `.codex`
- `static/uploads/`

## Update 2026-04-05
- Changed: Neuen Architektur-Sprint fuer DB-first Konsolidierung verteilter JSON-Zustandsdaten geplant und im Master-Plan verankert
- Files: `sprints/sprint-qs-db-first-state-consolidation.md`, `sprints/master-plan-2026-04-01.md`, `next-session.md`
- Verify: Inhaltlich gegen aktuelle Repo-Aufteilung `DB + Root-JSON + Markdown` geprueft und Migrationsreihenfolge fuer einfache JSON-Stores vor Marker-Runtime-State festgelegt
- Next: Entscheiden, ob zuerst QR Session 4 oder QS Phase 1 umgesetzt wird

## Update 2026-04-05
- Changed: Sprint QR Session 4 umgesetzt; der Planning-Service liefert jetzt Session-Summaries aus `last_session`, Marker/Tasks/Specs/Sprints zeigen ihre Session-Historie im Detailpanel, und Sessions koennen direkt aus dem Projekt-Planning geoeffnet werden
- Files: `services/plan_structure_service.py`, `static/js/project-planning.js`, `static/css/project-planning.css`, `tests/test_plan_structure_service.py`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `python3 -m py_compile services/plan_structure_service.py`, `node --check static/js/project-planning.js`, `pytest tests/test_plan_structure_service.py -q`
- Next: Im Browser mit echten Projekt-/Marker-Daten pruefen, ob die best-effort Task-Zuordnung ueber Markertitel robust genug ist oder spaeter eine explizitere Task-ID braucht

## Update 2026-04-05
- Changed: Live-Validierung fuer QR Session 4 nachgezogen und den Planning-Read-Pfad um einen klar gekennzeichneten Fallback auf echte Projektsessions erweitert, damit das Detailpanel auch bei leeren `last_session`-Feldern im aktuellen `handoff.md` nutzbaren Session-Kontext zeigt
- Files: `services/plan_structure_service.py`, `static/js/project-planning.js`, `tests/test_plan_structure_service.py`, `next-session.md`
- Verify: lokaler Restart `sudo systemctl restart project-dashboard`; Live-API `GET /api/projects/project_dashboard/planning` liefert jetzt `recent_sessions`; Bestand geprueft: `handoff.md` hat aktuell 8 Marker und 0 gesetzte `last_session`
- Next: Entweder Marker-Write-back kuenftig konsequent mit `last_session` fuellen oder einen expliziten Backfill fuer bestehende Marker planen, damit die Session-Historie von Fallback auf echte Task-Verknuepfung wechselt

## Update 2026-04-05
- Changed: `last_session`-Kontinuitaet umgesetzt; Handoff-Regeneration bewahrt jetzt bestehende Marker-Runtime-Felder, und ein neuer Backfill zieht leere `last_session`-Felder aus `project_plans.session_uuid` nach
- Files: `services/project_handoff_service.py`, `services/copilot_marker_service.py`, `scripts/backfill_marker_last_sessions.py`, `tests/test_project_handoff.py`, `tests/test_copilot_marker_service_flow.py`, `handoff.md`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `python3 -m py_compile services/copilot_marker_service.py services/project_handoff_service.py scripts/backfill_marker_last_sessions.py`, `pytest tests/test_copilot_marker_service_flow.py tests/test_project_handoff.py -q`; echter Backfill `python3 scripts/backfill_marker_last_sessions.py --project project_dashboard` ergab `updated: 7` bei `8` Markern
- Next: Den verbleibenden Marker ohne `last_session` pruefen und entscheiden, ob dafuer bewusst kein Session-Link existiert oder ein spezieller Fallback gebraucht wird

## Update 2026-04-05
- Changed: Hauptnavigation fachlogisch weiter vereinheitlicht; `Plan Index` heisst jetzt `Planning`, `Copilot` wird in der primaeren Navigation als `AI Workspace` gefuehrt, und `Sessions` wurde auf `Activity` umbenannt
- Files: `templates/base.html`, `templates/plans.html`, `templates/plan_detail.html`, `templates/copilot_landing.html`, `templates/copilot_board.html`, `templates/copilot.html`, `templates/sessions.html`, `templates/session_detail.html`, `templates/partials/index_modals.html`, `static/js/base.js`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/base.js`; Sichttexte in Sidebar, Breadcrumbs, Plan-Backlink und Command Palette vereinheitlicht; technische Routen wie `/copilot`, `/sessions` und `?tab=gitea` bleiben unveraendert
- Next: Restliche sichtbare Fachbegriffe rund um `Claude Sessions` und `Copilot` in Widgets, Landing-Texte und Detailmodule angleichen, falls die neue Navigationssprache durchgaengig ueber alle Screens gelten soll

## Update 2026-04-05
- Changed: Den redundanten Unterpunkt `Projects` entfernt; der Bereichsheader `Projects` oeffnet jetzt direkt die Hauptansicht, waehrend der Chevron separat nur das Submenue fuer `New Project`, `Overview` und `Repository Sources` schaltet
- Files: `templates/base.html`, `static/css/layout.css`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: Sidebar-Markup und CSS gegen bestehende `showTab('projects')`-Logik geprueft; keine Routen- oder JS-Logik fuer Tabs geaendert
- Next: Im Browser kurz pruefen, ob sich Klick auf `Projects` und Klick auf den Chevron im Desktop- und Mobile-Sidebar-Verhalten klar getrennt anfuehlen

## Update 2026-04-05
- Changed: Projektseite fachlich geschaerft; der Projekt-Tab `Overview` heisst jetzt `Details`, und oberhalb der Tabs rendert die Seite jetzt eine kartenbasierte Projektuebersicht fuer Plan-Fortschritt, Sprint-Plans, Quality-Issues und aktuelle Activity
- Files: `templates/project_detail.html`, `static/js/project-detail.js`, `static/css/project-detail.css`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/project-detail.js`; die neuen Cards lesen vorhandene Daten nur aus bestehenden APIs fuer Planning, Quality und Sessions, ohne neue Backend-Endpunkte
- Next: Im Browser auf echten Projekten pruefen, ob die Kartenreihenfolge und die Auswahl der Kennzahlen fachlich passen oder ob statt Quality-Issues eher Repo-Issues/GitHub-Issues prominenter gezeigt werden sollen

## Update 2026-04-05
- Changed: Die neue Projektuebersicht von reiner Statistik auf handlungsfuehrende `What Now`-Karten umgebaut; jede Karte formuliert jetzt eine Empfehlung und fuehrt direkt nach `Details`, `Planning`, `Quality` oder `Activity`
- Files: `static/js/project-detail.js`, `static/css/project-detail.css`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/project-detail.js`; die Karten nutzen weiter nur bestehende APIs, aber priorisieren jetzt naechste Aktionen statt nackter KPI-Ansammlung
- Next: Im laufenden UI pruefen, ob die Hauptkarte fachlich die richtige Prioritaet waehlt oder ob `Planning` immer der Default-Einstieg bleiben soll

## Update 2026-04-05
- Changed: Den primaeren KI-Arbeitsbereich sprachlich wieder auf `Cockpit` zurueckgezogen; Sidebar, Breadcrumbs und Seitentitel zeigen jetzt wieder denselben Fachbegriff statt `AI Workspace`
- Files: `templates/base.html`, `templates/copilot_landing.html`, `templates/copilot_board.html`, `templates/copilot.html`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: Reststellen auf sichtbares `AI Workspace` in Templates und ausgelieferten UI-Texten geprueft; technische Route `/copilot` bleibt unveraendert
- Next: Nach dem Restart kurz live pruefen, ob `Cockpit` in Sidebar und auf allen Copilot-Seiten konsistent erscheint

## Update 2026-04-05
- Changed: Projektkontext im Browser persistierbar gemacht; Projektseiten und projektbezogene Plan-/Cockpit-Einstiege speichern jetzt das aktive Projekt, und das `Cockpit` befuellt das Projektfeld beim Oeffnen automatisch wieder
- Files: `static/js/base.js`, `static/js/copilot.js`, `static/js/project-detail.js`, `static/js/project-planning.js`, `static/js/plan-detail.js`, `static/js/plans.js`, `next-session.md`, `sprints/master-plan-2026-04-01.md`
- Verify: `node --check static/js/base.js static/js/copilot.js static/js/project-detail.js static/js/project-planning.js static/js/plan-detail.js static/js/plans.js`; projektbezogene `Cockpit`-Links tragen jetzt zusaetzlich `project=` im Query-String mit
- Next: Live pruefen, ob das Projektfeld im `Cockpit` nach Wechseln zwischen Projektseite, Plan-Detail und globalem Plans-Index stabil auf dem letzten aktiven Projekt bleibt

## Update 2026-04-05
- Changed: Bewussten Testmarker fuer die Cockpit-Kontrolle in `project_dashboard` gesetzt
- Files: `handoff.md`, `next-session.md`
- Verify: Marker `test-cockpit-2026-04-05` mit Titel `TESTMARKER: Copilot-Kontrolle` auf `plan_id=142` angelegt; Gate ist offen (`is_activatable: true`)
- Next: Im Cockpit Plan `142` oeffnen und pruefen, wie Sichtbarkeit, Aktivierung, Marker-Kontext und Statuswechsel auf diesem Testmarker reagieren

## Update 2026-04-05
- Changed: Den aktiven Projektkontext jetzt auch auf globalen Filterseiten als Default eingezogen; `Planning`, `Sessions`, `Timesheets` und `Model Comparison` uebernehmen jetzt das zuletzt aktive Projekt, solange kein expliziter URL-Parameter gesetzt ist
- Files: `static/js/plans.js`, `static/js/sessions2.js`, `static/js/timesheets.js`, `static/js/model-comparison.js`, `next-session.md`
- Verify: `node --check static/js/plans.js static/js/sessions2.js static/js/timesheets.js static/js/model-comparison.js`; `Planning` liest jetzt `filters.project` aus dem aktiven Projektkontext, die anderen Seiten setzen bzw. lesen ihre Projektfilter entsprechend
- Next: Live pruefen, ob sich die Default-Filter fachlich richtig anfuehlen oder ob einzelne globale Seiten bewusst immer ungefiltert starten sollen

## Update 2026-04-05
- Changed: Rest-Audit fuer projektbezogenen Kontext nachgezogen; `Session Detail` setzt jetzt das Session-Projekt als aktiven Kontext, `Model Eval` uebernimmt und speichert den Projektkontext, und die `Cockpit`-Landing fuehrt aktive Plans projektbezogen ins Cockpit
- Files: `static/js/session-detail.js`, `static/js/model_eval.js`, `templates/copilot_landing.html`, `next-session.md`
- Verify: `node --check static/js/session-detail.js static/js/model_eval.js`; die `Cockpit`-Landing baut `project=` jetzt in aktive Plan-Links ein
- Next: Live einmal quer pruefen, ob der Projektkontext nach `Project -> Planning -> Plan Detail -> Cockpit -> Sessions -> Model Eval` stabil gleich bleibt
