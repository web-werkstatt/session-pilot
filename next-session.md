# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-03
> **Status:** Copilot Workspace Redesign (unfertig, Qualitaet unbefriedigend)
> **Naechste Aufgabe:** Copilot UI ueberarbeiten oder zuruecksetzen

---

## Was in dieser Session passiert ist (2026-04-03)

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

## Naechste Session — Empfohlene Vorgehensweise

### OPTION A: Copilot UI gezielt verbessern
1. Referenzbild nochmal studieren: `upload/ChatGPT Image 3. Apr. 2026, 11_49_55.png`
2. Marker-Board im Browser gegen echte `handoff.md` eines Projekts pruefen
3. Drag-&-Drop-Write-back und `Vorschlag uebernehmen` einmal live auf Port 5055 gegenchecken
4. AI-Task-Button fachlich auf Marker-Modell ausrichten oder bewusst deaktivieren
5. Weitere Copilot-Bausteine nur selektiv auf `ui-*` Komponenten migrieren
6. Gesamteindruck auf Linear/Vercel-Niveau bringen

### OPTION B: Auf letzten stabilen Stand zuruecksetzen
- `git diff HEAD` zeigt alle ungestagten Aenderungen
- Betroffene Dateien: copilot_board.html, copilot.css, copilot_board.js, copilot_routes.py, copilot_landing.html, copilot_landing.css
- Zuruecksetzen und dann sauber neu anfangen

### Offene Aufgaben (aus vorheriger Session)
- [ ] Copilot-Workflow: Perplexity als Copilot einsetzen
- [ ] LLM-agnostischer Connector (llm_connector.py)
- [ ] Pre-Commit Zeilenlimits fixen (db_service.py 526Z, governance_service.py 519Z)
- [ ] 6x bare except fixen
- [ ] 5x f-strings ohne Platzhalter (F541)
- [ ] 7x unused global Declarations (F824)

### Nicht vergessen
- **Referenzbild:** `upload/ChatGPT Image 3. Apr. 2026, 11_49_55.png`
- **Release-Skill:** `sessionpilot-release`
- **Level-Architektur:** /plans = Level 1, /copilot?plan_id=X = Level 2
- **Handoff-Service:** project_handoff_service.py
- **User-Erwartung:** Professionell, reduziert, dark, elegant — KEINE Marketing-UI, KEINE generische Kanban-Optik
