# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Fokusauftrag

1. Lies beim Start `sprints/master-plan-summary.md` als Rahmen. Wenn du Details zu einem bestimmten Sprint brauchst, lies die jeweilige Sprint-Datei unter `sprints/`.
2. Wenn `marker-context.md` existiert und nicht leer ist, behandle ihn als aktuellen Fokusauftrag.
3. Wenn kein `marker-context.md` existiert, frag nach, bevor du an einem Marker arbeitest.
4. Veraendere `marker-context.md` nie eigenmaechtig, ausser auf ausdruecklichen Auftrag.

## Projekt

Flask-basiertes Web-Dashboard zur Verwaltung und Uebersicht aller Projekte unter `/mnt/projects/` sowie Docker-Container und Claude Code Sessions. Laeuft als systemd-Service (`project-dashboard`) auf Port 5055. Installierbar via Docker oder setup.sh.

## Befehle

```bash
# Entwicklung: App manuell starten
python3 app.py

# Produktion: systemd-Service
sudo systemctl restart project-dashboard
sudo systemctl status project-dashboard

# Logs
tail -f /mnt/projects/project_dashboard/dashboard.log

# Docker (Alternative)
docker compose up -d
```

Kein Build-Schritt, keine Tests, kein Linting konfiguriert. Abhaengigkeiten in `requirements.txt` (Flask, markdown, psycopg2-binary, openpyxl).

## Architektur

**Einstiegspunkt:** `app.py` — Flask-App, registriert Blueprints, startet Notification-Checker, laedt .env.

Detail-Listen der Route-Module und Services befinden sich in den jeweiligen Unterverzeichnis-CLAUDE.md Dateien (`routes/CLAUDE.md`, `services/CLAUDE.md`), die automatisch geladen werden wenn dort gearbeitet wird.

**Konfiguration:** `config.py` laedt alle Werte via `os.environ` mit Defaults. Secrets in `.env`-Datei, geladen via systemd `EnvironmentFile`.

## Verbote

- **Kein `python3 -c` und kein eigenes `psycopg2.connect()`** fuer DB-Zugriffe oder Tests. Ausschliesslich die vorhandenen DB-Funktionen und Service-Schicht im Projekt nutzen. DB-Struktur durch Code-Lesen verstehen, nicht durch Abfragen ans Running-System.
- **Bestehenden manuell geschriebenen Text nie kuerzen, umformulieren oder zusammenfassen.** Gilt fuer `next-session.md`, `handoff.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` und alle Sprint-Dokumente unter `sprints/`. Nur ergaenzen (neue Bloecke/Zeilen anfuegen) oder in klar markierten generierten Bloecken (`<!-- DASHBOARD-GENERATED:START ... -->`) ueberschreiben. Unmarkierter Text gilt als manuell und ist schreibgeschuetzt.

## Schreib-Policies pro Datei

| Datei | Policy | Bedeutung |
|---|---|---|
| `next-session.md` | **append-only** | Neue Bloecke/Historie anfuegen, bestehende Zeilen nie aendern oder loeschen |
| `handoff.md` | **generated-blocks-only** | Nur `<!-- DASHBOARD-GENERATED:START -->` Bereiche ueberschreiben, Rest ist tabu |
| `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` | **generated-blocks-only** | Nur markierte Bereiche ueberschreiben, manueller Text ist geschuetzt |
| `sprints/*.md` | **append-only** | Nachtraege anfuegen (z.B. ADR-Verweise), bestehenden Text nie aendern |
| `marker-context.md` | **nie eigenmaechtig** | Nur auf ausdruecklichen Auftrag (siehe Fokusauftrag) |

### Block-Marker-Konvention

```markdown
<!-- MANUAL:START owner=joseph -->
...manuell geschriebener Kontext, fuer Executor/Services schreibgeschuetzt...
<!-- MANUAL:END -->

<!-- DASHBOARD-GENERATED:START source=workflow_core updated=2026-04-10 -->
...automatisch generierter Inhalt, darf nur vom zustaendigen Service ueberschrieben werden...
<!-- DASHBOARD-GENERATED:END -->
```

- `MANUAL`-Bloecke: fuer jeden Executor und Service schreibgeschuetzt, keine Ausnahme.
- `DASHBOARD-GENERATED`-Bloecke: duerfen nur vom im `source`-Attribut genannten Service ueberschrieben werden.
- Unmarkierter Text: gilt als manuell (= geschuetzt), bis explizit als generiert markiert.

## Wichtige Patterns (Verbote und Pflicht-Nutzung)

Detaillierte Architektur-Beschreibungen befinden sich in den Unterverzeichnis-CLAUDE.md Dateien (`routes/`, `services/`, `static/`, `templates/`, `sprints/`).

- **Pfad-Aufloesung:** Immer `services/path_resolver.py:resolve_project_path()` nutzen, nie manuell.
- **Tag-Erkennung:** `project_detector.py:detect_tags()` ist zentral — NICHT duplizieren.
- **Fetch-Wrapper:** KEIN rohes `fetch()` in Seiten-JS. Immer `api.get()`, `api.post()` etc. aus `static/js/api.js`.
- **Globale JS-Utilities:** `base.js` Funktionen NICHT in einzelnen JS-Dateien duplizieren.
- **Modal-System:** KEINE eigenen Escape-Handler. Immer `openModal(id)`/`closeModal(id)` aus `base.js`.
- **Error-Handling:** `@api_route` Decorator aus `routes/api_utils.py` statt try/except.
- **Shared Helpers:** Session-Meta-Felder IMMER in `session_import_utils.py` aendern, nicht in Importern.
- **Plan-Handoff:** Handoff ist IMMER aus DB abgeleitet — nie manuell in .md pflegen.
- **Plan-Sections:** Board-Spalten nutzen `status`, NICHT `workflow_stage`.

## Workflow: Issues bei Aenderungen

Bei **jeder Code-Aenderung** (neue Features, Bugfixes, Refactoring) wird ein Gitea-Issue erstellt:
1. **Vor der Arbeit:** Issue auf Gitea anlegen
2. **Im Commit:** Issue-Nummer referenzieren (`fixes #N` oder `refs #N`)
3. **Nach Abschluss:** Issue schliessen

**Ausnahmen** (kein Issue noetig): Doku-Updates, Typo-Fixes <5 Zeilen, generierte Dateien.

**GitHub-Mirror:** `git push github main`. Issues nur auf Gitea.

## Betrieb

Befehle, Scheduled Tasks, RemoteTrigger und Backup-Details: Skill `/project-ops` laden.

## Handoff- und Prioritaetslogik (ab 2026-04-17)

Diese Regel hat Vorrang vor Punkt 1 des `## Fokusauftrag`-Blocks oben,
wenn sich Angaben widersprechen. Punkt 2-4 des Fokusauftrags
(`marker-context.md`) bleiben unveraendert.

Verbindliche Lese-Reihenfolge fuer Kontextaufnahme:

1. `next-session.md` — ausschliesslich fuer aktuellen Kurzstatus, naechste
   Aufgabe und operative Hinweise. Schlanker Handoff, keine Langchronik.
2. `sprints/NOW-next-critical-path.md` — primaere operative
   Prioritaetsdatei. Bestimmt, was JETZT, als NAECHSTES und SPAETER
   relevant ist.
3. themenspezifische Sprint-Datei passend zur aktuellen Aufgabe, z.B.:
   - Agent-Orchestrator Foundation:
     `sprints/sprint-agent-orchestrator-phase-1-foundation.md`
   - Handoff-/Marker-Resolver:
     `sprints/sprint-agent-orchestrator-5-day-execution-plan.md`
     + `docs/agent-orchestrator-hardening-technical-spec.md`
   - historische Einordnung Recursive-Scanner:
     `sprints/sprint-full-project-recursive-plan-scanner.md`
4. historische Details nur bei Bedarf:
   - `sprints/master-plan-2026-04-01.md` — nur fuer historische
     Sprint-Historie, nicht fuer unmittelbaren Critical Path.
   - `docs/next-session-archive-2026-04-05.md` — nur fuer alte
     Entscheidungen oder Recovery-Kontext. Niemals primaer daraus
     arbeiten.

Arbeitsregeln:

- `next-session.md` nicht als Langchronik lesen.
- `docs/next-session-archive-2026-04-05.md` nicht fuer aktuelle
  Priorisierung.
- `sprints/master-plan-2026-04-01.md` nur fuer historische Sprint-Historie,
  nicht fuer den unmittelbaren Critical Path.
- Wenn alte Session-Bloecke oder archivierte Update-Texte etwas anderes
  sagen als die neuen operativen Dateien, gelten die neuen Dateien.

Aktueller Stand, der zu respektieren ist:

- `project_recursive`-Scanner ist live verifiziert, bereinigt und nicht mehr
  Hauptbaustelle.
- Offener Hauptfokus:
  1. Agent-Orchestrator Phase 1
  2. Handoff-/Marker-Resolver
- Scanner-Tuning ist aktuell kein Default-Scope.

Antwortverhalten bei neuer Aufgabe:

- Am Anfang der Session oder neuen Aufgabe kurz nennen:
  - welche der Prioritaetsdateien gelesen wurden
  - welche davon fuer den aktuellen Auftrag fuehrend ist

