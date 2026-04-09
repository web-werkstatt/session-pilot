# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-09 (Session-Detail Navigation, TOC und Sidebar-Hotfixes deploy-ready)
> **Status:** Reaktiviert fuer Sprint CP. `v1.3-final` bleibt letzter Freeze-Tag, die Projektseite `/project/<name>` wird jetzt gezielt zur Control Plane vereinfacht.
> **Naechste Aufgabe:** Naechsten Produkt-/Sprint-Schnitt fuer die Control Plane waehlen; Workflow-Loop v1 und der entschlackte Planning-Tab sind abgeschlossen. Letzter UI-Hotfix korrigiert den Ruecksprung aus Session-Details zur Planning-Ansicht.

---

## Was gilt jetzt

Der Freeze-Stand **`v1.3-final`** bleibt als stabile Basis erhalten. Seit 2026-04-08
ist das Repo jedoch gezielt fuer Sprint CP reaktiviert: Fokus ist nicht eine neue
Feature-Welle, sondern die Vereinfachung von `/project/<name>` zur klaren Control
Plane, waehrend `/copilot?...` Execution Workspace bleibt. Alle Deferred-Sprints aus
dem Closeout bleiben weiterhin deferred; der laufende Strang ist nur Sprint CP.

## Was funktioniert (= Bestand der v1.3-final)

| Bereich | Status |
|---|---|
| Session-Verwaltung | DONE — Multi-Account, Live-Viewer, Reviews, Export |
| Plans-Import + Detail | DONE — `/plans` mit Tabs, Sprint-Plans-Liste |
| Cockpit / Copilot-Board | DONE — Marker-Cards, Drag&Drop, Chat-Kontext, Session-Marker-Binding (Sprint SB) |
| Quality Scanner | DONE — `/quality` mit 7 Checks, Baseline/Diff |
| Governance Light (Sprint C) | DONE — `/governance` mit Policy-Levels, Gate-Ampel, Rules, Effectiveness, Snippets |
| LLM Command Hub MVP | DONE — `/llm-commands` mit 3+ Start-Commands |
| Audit Core + Integration | DONE — `/audits` mit Run-Trigger, Requirements, LLM-Reviews |
| Usage Monitor | DONE — Live-JSONL, P90-Limits, OTel-Empfaenger |
| Sprint-Flow als Markdown | DONE als Datei-basiert (DB-Variante deferred = Sprint 14) |
| Backup taeglich | DONE — Cron 12:30, 7-Tage-Rotation |

## Was nicht da ist (= Deferred)

Siehe Master-Plan, Block "Deferred Sprints (post-closeout v1.3-final)".

## Wie naechste Session starten

Wenn du das Dashboard wieder anfasst (z.B. um einen deferred Sprint zu reaktivieren):

1. Dieses File zuerst lesen
2. Master-Plan ueberfliegen — vor allem den "Deferred"-Block
3. Gewuenschten Sprint aus `sprints/` waehlen, neuen Sprint-Plan anlegen
4. `v1.3-final` als Ausgangspunkt: `git diff v1.3-final`

Bis dahin: Dashboard laeuft als systemd-Service auf Port 5055, Backup taeglich
12:30, keine aktive Entwicklung noetig.

## Operative Hinweise

- **Service:** `sudo systemctl status project-dashboard` (active expected)
- **Logs:** `tail -f /mnt/projects/project_dashboard/dashboard.log`
- **Backup-Verzeichnis:** `/mnt/projects/backups/project-dashboard/daily/`
- **Backup manuell ausloesen:** `/mnt/projects/project_dashboard/scripts/backup.sh daily`
- **Cron-Zeiten:** daily 12:30, weekly Sonntag 13:30 (mittags weil Workstation nachts aus)
- **DB:** PostgreSQL `project_dashboard`, Schema-Migrationen lazy via `ensure_*_schema()`
- **Marker-Context:** `marker-context.md` im Root ist Runtime-Datei (gitignored), CLAUDE.md-Regel: nie eigenmaechtig veraendern

## Historie

- **2026-04-09:** Session-Detailseite entkoppelt den Breadcrumb vom Rueck-CTA: statt `Workspace / Zurueck / Detail` zeigt der Breadcrumb wieder nur Kontext (`Planning` bzw. Fallback `Activity`), und Session-Links aus dem Projekt-Planning tragen jetzt ein explizites Rueckziel auf `/project/<name>?tab=plans`, sodass `Zurueck` verlaesslich wieder im Planning-Tab landet (`templates/session_detail.html`, `static/js/session-detail.js`, `static/js/project-planning.js`).
- **2026-04-09:** Session-Detail-TOC lesbarer gemacht: Nummer/Text stehen sauber nebeneinander, User-Eintraege zeigen mehr Hoehe, und die Preview kuerzt jetzt weich an Wortgrenzen mit `...` statt hart mitten im Wort; aktueller Preview-Cut ist 75 Zeichen (`static/css/session-detail.css`, `static/js/session-toc.js`).
- **2026-04-09:** `Projects` im Sidebar-Menue bekam einen staerkeren aktiven Hintergrund, damit der Parent-Link GUI-seitig klarer als aktiver Navigationspunkt erkennbar ist (`static/css/sidebar-submenu.css`).
- **2026-04-09:** `Quality` auf der Projektseite signalisiert jetzt den Report-Status direkt im Sekundaerlink: `No Scan` ohne Report, farbige States fuer gut/warnend/kritisch je Score sowie `Scanning` waehrend eines laufenden Scans (`templates/project_detail.html`, `static/js/project-detail.js`, `static/css/project-detail.css`).
- **2026-04-09:** Governance-Uebersicht auf Entscheidungslogik vereinfacht: klarer Einstiegstext, Tabs sprachlich entabstrahiert, Projekt-Tabelle von Metrikspalten auf `Status`, `Warum`, `Policy`, `Aktivitaet` reduziert und Gate-Gruende direkt sichtbar statt nur als Tooltip-Ampel; Fehlermuster-Tab ebenfalls klarer beschrieben (`templates/governance.html`, `static/js/governance.js`, `static/css/governance.css`).
- **2026-04-09:** Governance-KPI-Zeile visuell abgeschwaecht: kleinere Zahlen, weniger Padding und weniger dominante Karten, damit der eigentliche Entscheidungsbereich nicht von der Statistik ueberlagert wird (`static/css/governance.css`).
- **2026-04-09:** Reinen Statistik-/Muster-Tab aus der zentralen Governance-Seite entfernt. `/governance` zeigt jetzt nur noch die operative Entscheidungsansicht; die Meta-Analyse ist kein Hauptnavigationsziel mehr (`templates/governance.html`, `static/js/governance.js`).
- **2026-04-09:** Redundante Status-Legende (`OK`, `Pruefen`, `Kritisch`) aus dem Governance-Intro entfernt; die Bedeutung steckt bereits direkt in den Status-Badges der Tabelle (`templates/governance.html`, `static/css/governance.css`).
- **2026-04-09:** `/quality` GUI/UX grundlegend nachgeschaerft: neuer Intro-/Arbeitsmodus-Bereich, kompakteres Playbook, risikoorientierte Projektliste mit `Risk`-Spalte und staerkerer Detailansicht (`Quality Briefing`, Focus-/Next-Step-Karten) statt nur flacher Rohzahlen-Tabelle (`templates/quality.html`, `static/js/quality.js`, `static/css/quality.css`).
- **2026-04-09:** Monorepo-Detailseiten im Bereich `Details` substanziell verbessert: neue `Structure`-Section aus `project.json.subprojects` sowie `Root Orientation` mit wichtigen Root-Dokumenten und Pfaden, damit Projekte wie `/project/auth-stack` nicht mehr leer wirken (`routes/project_info_routes.py`).
- **2026-04-08:** `Open Planning` aus ausgewahlter Sprint-/Spec-Ansicht im Projekt-Planning fuehrt jetzt gezielt auf die zugehoerige Plan-Detailseite statt nur in den generischen `/plans?project=...`-Workspace; der Plan-Level-Link bleibt weiter auf dem Workspace (`static/js/project-planning.js`).
- **2026-04-08:** Leisen Empty-State im Projekt-Planning weiter reduziert: der Hinweis `No sprint hierarchy detected in this plan yet.` wurde entfernt; ein Plan ohne Sprint-Hierarchie erscheint jetzt einfach ohne zusaetzlichen Warntext (`static/js/project-planning.js`).
- **2026-04-08:** Verbleibende Statistikzeilen aus der rechten Spec-Karte im Projekt-Planning entfernt: `Tasks`, `Mapped Tasks` und `Linked Sessions` sind dort nicht mehr sichtbar (`static/js/project-planning.js`).
- **2026-04-08:** Spec-Auswahl im Projekt-Planning wieder separat klickbar gemacht: Klick auf eine Spec stoppt jetzt das Bubbling zur uebergeordneten Sprint-Karte, sodass Sprint-Auswahl die Spec nicht mehr sofort ueberschreibt (`static/js/project-planning.js`).
- **2026-04-08:** Rechte Sprint-Karte im Projekt-Planning komplett entleert von Metadaten: auch `Summary`, `Sprint Tag`, `Plan ID` und `Linked Sessions` entfernt, damit rechts bei Sprint-Auswahl nur noch Scope-Hinweis und CTA bleiben (`static/js/project-planning.js`).
- **2026-04-08:** Rechte Sprint-Statistik im Projekt-Planning wieder entfernt: `Specs`, `Tasks` und `Mapped Tasks` waren dort redundant zur linken Strukturansicht und wurden aus dem Kontextpanel gestrichen (`static/js/project-planning.js`).
- **2026-04-08:** Sprint-Kontext im rechten Planning-Panel zaehlt Arbeit jetzt korrekt ueber den ganzen Sprint: statt irrefuehrendem `Direct Tasks` werden `Tasks` und `Mapped Tasks` inklusive Spec-Unterstruktur angezeigt (`static/js/project-planning.js`).
- **2026-04-08:** Rechte Planning-Kontextkarte scrollt wieder vollstaendig lesbar: Sticky-Verhalten entfernt und stattdessen automatischer Scroll zur Detailkarte nach Sprint-/Spec-Auswahl eingefuehrt (`static/css/project-planning.css`, `static/js/project-planning.js`).
- **2026-04-08:** Rechter Plan-Kontext im Projekt-Planning komplett auf Navigation reduziert: auch die Summary entfernt, damit bei Plan-Auswahl keine redundante Inhaltswiederholung mehr rechts erscheint (`static/js/project-planning.js`).
- **2026-04-08:** Rechter Plan-Kontext im Projekt-Planning weiter reduziert: auch `Status` und `Plan ID` entfernt, sodass bei Plan-Auswahl nur noch die eigentliche Summary plus Navigation bleibt (`static/js/project-planning.js`).
- **2026-04-08:** Redundante Zaehler aus dem rechten Plan-Kontext im Projekt-Planning entfernt: `Sprints`, `Specs` und `Direct Tasks` bleiben links in der Plan-Card, rechts steht fuer Plan-Auswahl nur noch der eigentliche Kontext (`static/js/project-planning.js`).
- **2026-04-08:** Ruecksprung aus `/plans?project=<name>` landet jetzt direkt im Planning-Tab der Projektseite: Back-Link setzt `?tab=plans`, und die Projektseite wertet `tab=plans` bzw. `tab=planning` beim Laden aus (`static/js/plans.js`, `static/js/project-detail.js`).
- **2026-04-08:** Ruecksprung auf `/plans?project=<name>` mit mehr Abstand nach oben versehen, damit der Button nicht mehr so dicht unter der Sticky-Zone klebt (`templates/plans.html`, `static/css/plans.css`).
- **2026-04-08:** `/plans?project=<name>` zeigt jetzt wieder einen klaren Ruecksprung ins Projekt: kontextsensitiver `Zurueck zum Projekt`-Button oben auf der Plans-Seite, nur wenn die Seite mit Projektfilter geoeffnet wurde (`templates/plans.html`, `static/js/plans.js`).
- **2026-04-08:** Projekt-Dashboard-Planning verlinkt nicht mehr falsch auf die alte Einzel-Plan-Detailseite: Plan-Titel und Sekundaer-CTA fuehren jetzt aus `/project/<name>` in den zentralen `/plans?project=<name>`-Arbeitsbereich (`static/js/project-planning.js`).
- **2026-04-08:** Planning-Kontext rechts wieder sichtbar gehalten ohne zweiten Scrollbar: Panel ist jetzt erneut `sticky`, aber ohne `max-height` und ohne internes `overflow`, damit man nach Plan-Auswahl nicht immer nach oben springen muss (`static/css/project-planning.css`).
- **2026-04-08:** Planning-Kontextspalte scrollt wieder im normalen Seitenfluss: eigener Sticky-/Overflow-Container entfernt, damit kein zweiter Scrollbar mehr entsteht und Inhalte rechts nicht mehr abgeschnitten wirken (`static/css/project-planning.css`).
- **2026-04-08:** Kleiner Layout-Hotfix fuer den Planning-Tab: die Plan-Card scrollt wieder voll sichtbar, nachdem die negative Aussenmarge am klickbaren Plan-Header entfernt wurde (`static/css/project-planning.css`).
- **2026-04-08:** Planning-Tab entmischt: links bleiben Plans/Sprints/Specs mit Tasks und Markern nur noch als untergeordnete Listenpunkte, rechts zeigt der Kontextbereich jetzt ausschliesslich Plan-, Sprint- und Spec-Kontext statt operativem Task-/Marker-Inspector (`static/js/project-planning.js`, `static/css/project-planning.css`). Verifiziert mit `node --check static/js/project-planning.js` und `pytest -q tests/test_routes_smoke.py tests/test_workflow_loop_route.py` => `112 passed`.
- **2026-04-08:** TOC-Scrollabstand auf der Projektseite nachgezogen: Inhaltslinks landen jetzt mit mehr Abstand unter der sticky Navigation (`static/css/project-detail.css` via `scroll-margin-top`).
- **2026-04-08:** Projekt-Description-Fehler behoben: kaputtes trailing `<br` aus `project.json` entfernt und zusaetzlich den Description-/Subtitle-Renderpfad gegen halb kaputte HTML-Reste gehaertet (`routes/project_info_routes.py`, `static/js/project-detail.js`). Verifiziert mit `python3 -m py_compile routes/project_info_routes.py`, `node --check static/js/project-detail.js` und `pytest -q tests/test_routes_smoke.py tests/test_workflow_loop_route.py` => `112 passed`.
- **2026-04-08:** Zweiter Reduktionsschnitt fuer `/project/<name>`: Hauptnavigation auf `Details`, `Planning`, `Workflow` reduziert. `Documents`, `Quality`, `Governance`, `AI Heatmap` und `Activity` erscheinen jetzt als leisere Sekundaer-Links statt gleichrangiger Haupttabs. Verifiziert mit `pytest -q tests/test_routes_smoke.py tests/test_workflow_loop_route.py` => `112 passed`.
- **2026-04-08:** Projektseite strukturell entschaerft: obere Overview-Cards entfernt, `Workflow` als eigener Haupttab eingefuehrt und der Workflow Loop aus `Details` in diesen Tab verschoben. `Details` bleibt wieder reiner Projektdetail-Bereich, `Planning` bleibt separat. `project-overview-cards.js` ist nicht mehr an die Projektseite gebunden. Verifiziert mit `node --check static/js/project-detail.js` und `pytest -q tests/test_routes_smoke.py tests/test_workflow_loop_route.py` => `112 passed`.
- **2026-04-08:** Sprint CP fachlich abgeschlossen: Copilot-Workspace zeigt fuer markergebundene Chats jetzt sichtbar `Thread fortsetzen` vs. `Neuen Thread starten`, Marker ohne Rating zeigen `Abschluss unvollstaendig` und fuehren gezielt in den History-/Rating-Kontext. Workflow-Loop-Renderer auf der Projektseite hat robuste Busy-/Responsive-/A11y-Kanten erhalten. Laufend verifiziert via App-Smoke und kombinierter Regression.
- **2026-04-08:** Sprint-CP-Stand mit Workflow-Loop v1 deployt. Commit `4d70fc3` nach `main` gepusht, `project-dashboard` per systemd neu gestartet und lokal gegen die laufende App geprueft: `/copilot?plan_id=141`, `/static/js/plans.js` und `GET /api/project/project_dashboard/workflow-loop` antworten. Kombinierter Regression-Lauf: `203 passed`.
- **2026-04-08:** Read-only-GETs fuer Smoke-/Degraded-Betrieb gehaertet: `routes/section_routes.py` registriert und abgesichert, `/copilot` ohne `plan_id` rendert jetzt Landing statt Redirect-only, mehrere GET-APIs liefern bei fehlender DB leere valide JSON-Strukturen statt `500` (`routes/api_utils.py`, `routes/session_routes.py`, `routes/session_analysis_routes.py`, `routes/plans_routes.py`, `routes/widget_routes.py`, `routes/copilot_routes.py`, `routes/audit_routes.py`, `services/session_validation_service.py`). Verifiziert mit `pytest -q tests/test_routes_smoke.py` => `110 passed`.
- **2026-04-08:** Workflow-Loop v1 fuer Sprint CP begonnen und technisch umgesetzt: neues Aggregationsmodul `services/workflow_loop_service.py`, neuer Endpoint `GET /api/project/<name>/workflow-loop`, Shell in `templates/project_detail.html`, neue Frontend-Dateien `static/js/workflow-loop.js`, `static/js/workflow-loop-svg.js`, `static/css/workflow-loop.css`, initiale Deep-Link-Oeffnung in `static/js/copilot_board.js` fuer `marker_id`/`tab`, Tests in `tests/test_workflow_loop_service.py` und `tests/test_workflow_loop_route.py`. Verifiziert mit `pytest -q tests/test_workflow_loop_service.py tests/test_workflow_loop_route.py`, `python3 -m py_compile services/workflow_loop_service.py routes/project_routes.py` und `node --check` fuer die neuen/angepassten JS-Dateien.
- **2026-04-08:** Zwei praezise Implementierungsdokumente fuer den Workflow Loop erstellt: `sprints/sprint-cp-workflow-loop-implementation.md` und `sprints/sprint-cp-workflow-loop-contracts.md`. Enthalten Arbeitspakete, API-Contract, DOM-Schnitt, CTA-Regeln und feste No-Decisions fuer die Umsetzung.
- **2026-04-08:** Technischer UI-Schnitt fuer den Workflow-Loop in `sprints/sprint-cp-workflow-loop-technical-cut.md` dokumentiert. Festgezogen: Flask/Jinja-Shell auf `/project/<name>`, separater JSON-Endpoint, Vanilla-JS-Controller und SVG-Renderer fuer den Ring.
- **2026-04-08:** Produktentscheidung fuer Sprint CP erweitert: Audit-, Governance- und Quality-Signale werden als lesbarer Priorisierungskontext mit expliziten Hinweisen eingebunden, aber ohne automatische Re-Sortierung oder harte Gates. AC15-AC16 und Microcopy (`bevorzugt bearbeiten`, `Quality-kritisch`) in die Sprint-Dokumente aufgenommen.
- **2026-04-08:** Produktentscheidung fuer Sprint CP erweitert: `done` ohne Rating wird als sichtbarer Zwischenzustand `Abschluss unvollstaendig` gefuehrt. AC12-AC14 und Microcopy (`Abschluss unvollstaendig`, `Rating nachholen`) in die Sprint-Dokumente aufgenommen.
- **2026-04-08:** Produktentscheidung fuer Sprint CP festgezogen: markergebundene Chats werden als explizit fortsetzbare Marker-Threads modelliert. AC9-AC11 und Microcopy-Linie (`Thread fortsetzen` / `Neuen Thread starten`) in die Sprint-Dokumente aufgenommen.
- **2026-04-08:** Chat-Unterstuetzung fuer Sprint CP explizit in `sprints/sprint-cp-ux-ui-target-picture.md` und `sprints/sprint-cp-control-plane-loop-closure.md` verankert. Fokus: Plan-Chat ohne aktiven Marker vs. markergebundene Execution mit sichtbarem Thread-Fortsetzungszustand.
- **2026-04-08:** UX/UI-Zielbild als neues Diskussionsdokument `sprints/sprint-cp-ux-ui-target-picture.md` erstellt. Kerngedanke: `/project/<name>` als Control Plane, `/copilot?plan_id=...` als Execution Workspace mit explizitem Abschluss-Flow.
- **2026-04-08:** Neuer Sprint-Plan `sprints/sprint-cp-control-plane-loop-closure.md` aus dem Workflow-Dokument abgeleitet. Fokus: Gate -> Aktivierung -> Execution -> Write-back -> Rating -> naechster Marker als geschlossener Control-Plane-Loop.
- **2026-04-08:** Neues internes Workflow-Dokument `sprints/workflow-control-plane-loop.md` erstellt; beschreibt den SessionPilot-Workflow als zyklischen Control-Plane-Loop mit Gate, `marker-context.md`, Post-Execution-Write-back und Execution-Rating. Hilfe-Center-Eintrag wieder entfernt, weil das Thema in die Sprint-/Systemdoku gehoert.
- **2026-04-07 vormittags:** Sprint SB DONE (Session-Marker-Binding hart in DB), Tag-Commit `0bac136`
- **2026-04-07 nachmittags:** Closeout durchgefuehrt (M1-M14), Tag `v1.3-final`
- **Davor:** siehe `master-plan-2026-04-01.md` Section "Completed Sprints"
