# Plan: Voll funktionsfaehiges Workflow-System im Project Dashboard #sprint-plan-voll-funktionsfaehiges-workflow-system-im-project-dashboard

## Context
Das aktuelle Workflow-Tab im Project Dashboard zeigt bereits echte Daten aus Markern, Sessions, Ratings und Risiko-Hinweisen. Es ist aber noch vor allem eine Status- und Navigationsansicht. Die Visualisierung funktioniert, doch der Workflow wird noch nicht direkt im Tab gesteuert.

Projektpfad: /mnt/projects/project_dashboard
Zielbereich: Projekt-Detailseite, Tab `Workflow`

Aktueller Stand:
- Der Workflow Loop rendert echte Daten aus `/api/project/<name>/workflow-loop`.
- Die Grafik und Karten visualisieren den Zustand aus Markern, Plans, Ratings und Signalen.
- Deep-Links in Copilot, Planning und Execution existieren.
- Es fehlen aber direkte Workflow-Aktionen, persistente Statuswechsel, klare Transition-Regeln und eine saubere Rueckkopplung aus der operativen Arbeit.

Ziel dieses Plans:
Den Workflow-Tab von einer reinen Anzeige zu einem voll funktionsfaehigen operativen Workflow-System ausbauen, inklusive echter Aktionen, belastbarer Zustandslogik und verstaendlicher Fortschrittsanzeige in Grafik und UI.

## Sprint 1 - Workflow-Datenmodell und Zustandslogik #sprint-workflow-model
Goal: Ein sauberes, persistentes Workflow-Modell schaffen, auf dem Grafik und Aktionen verlaesslich aufbauen koennen.
**Status: DONE** (implementiert 2026-04-09)

### Persistente Marker-Workflow-States #spec-marker-workflow-states ✅
- **DONE:** `marker_workflow_states` Tabelle in `services/db_workflow_state_schema.py`.
- Statuswerte: `planned`, `ready`, `active`, `write_back`, `rating`, `done`, `blocked`.
- Felder: `started_at`, `completed_at`, `blocked_reason`, `owner`, `last_session`, `last_transition_at`.
- Schema lazy via `ensure_workflow_state_schema()` in `db_service.py`.
- Bestehende Marker werden beim Workflow-Loop-Abruf automatisch synchronisiert (`sync_marker_to_workflow()`).

### Transition-Regeln und Guardrails #spec-workflow-transitions ✅
- **DONE:** Explizite `ALLOWED_TRANSITIONS`-Map in `services/workflow_state_service.py`.
- Ungueltige Wechsel (z.B. `planned -> done`) werden mit `ValueError` abgewiesen.
- Automatische Feld-Updates (z.B. `started_at` bei `active`, `completed_at` bei `done`).
- `workflow_transitions`-Tabelle als Audit-Trail fuer jeden Statuswechsel.

### Workflow-API fuer Lesen und Schreiben #spec-workflow-api ✅
- **DONE:** REST-Endpoints in `routes/workflow_routes.py`:
  - `GET /api/project/<name>/workflow-states` — alle States eines Projekts
  - `GET /api/project/<name>/workflow-state/<marker_id>` — einzelner State + erlaubte Transitions
  - `POST /api/project/<name>/workflow-state/<marker_id>/transition` — Statuswechsel ausfuehren
  - `GET /api/project/<name>/workflow-state/<marker_id>/history` — Transition-Historie
  - `POST /api/project/<name>/workflow-sync` — Bulk-Sync aus handoff.md
- `workflow_loop_service.py` liefert `workflow_states` Map im Response.

## Sprint 2 - Echte Aktionen direkt im Workflow-Tab #sprint-workflow-actions
Goal: Aus dem Workflow-Tab heraus echte operative Steuerung ermoeglichen.

### Marker direkt starten und uebernehmen #spec-start-and-assign
- Fuege Aktionen wie `Start`, `Uebernehmen`, `Blockieren`, `Reaktivieren` direkt in Karten oder Detail-Drawer ein.
- Zeige klar, wer aktuell an einem Marker arbeitet.
- Verhindere konkurrierende Mehrfach-Aktivierungen ohne sichtbaren Hinweis.

**GUI/UX-Spec:**
- Jede Marker-Card bekommt einen CTA-Button-Bereich rechts unten.
- Button-Labels kontextsensitiv: `Starten` (planned/ready), `Uebernehmen` (active, anderer Owner), `Blockieren` (active), `Reaktivieren` (blocked/done).
- Buttons rufen `POST .../transition` auf und aktualisieren die Card inline (kein Page-Reload).
- Owner-Badge oben rechts an der Card: Avatar/Initial + Name, grau wenn kein Owner.
- Bei Mehrfach-Aktivierung: Confirm-Dialog „Marker X ist bereits aktiv bei Y. Trotzdem uebernehmen?".
- CSS: `.workflow-card__actions` flex-row gap-8, Buttons nutzen bestehende `.btn-sm` Varianten.

### Abschluss und Write-Back direkt im Tab #spec-complete-and-writeback
- Ermoegliche `Execution abgeschlossen`, `Write-back erledigt` und `Ergebnis dokumentiert` direkt im Workflow.
- Zeige fuer abgeschlossene Arbeit an, ob der Rueckkanal ins Planning oder in Marker-Notizen bereits sauber erfolgt ist.
- Reduziere Medienbrueche zwischen Workflow, Copilot und Planning.

**GUI/UX-Spec:**
- Write-Back-Schritt als eigene Inline-Checkliste in der Card: `[ ] Ergebnis in Plan dokumentiert`, `[ ] marker-context.md aktualisiert`, `[ ] Naechsten Schritt definiert`.
- Haken setzen loest keinen Status-Wechsel aus — erst expliziter Button `Write-back abschliessen` wechselt zu `rating`.
- Abgeschlossener Write-back zeigt gruenen Haken-Badge statt Checkliste.
- Fehlender Write-back bei `done`-Status: gelber Hinweis-Banner „Write-back unvollstaendig".

### Rating und Blocker direkt bearbeiten #spec-rating-and-blockers
- Offene Ratings muessen direkt im Workflow gesetzt werden koennen.
- Blocker brauchen sichtbare Gruende, Verantwortlichkeit und einen Weg zur Aufloesung.
- Der Workflow-Tab soll klar trennen zwischen `operativ offen`, `wartet auf Bewertung` und `blockiert`.

**GUI/UX-Spec:**
- Rating-Eingabe als kompaktes Inline-Widget: 1-5 Sterne oder Zahleneingabe + optionaler Kommentar.
- Rating-Widget erscheint automatisch in Cards mit Status `rating`.
- Blocker-Eingabe: Textarea fuer `blocked_reason` + `Blockieren`-Button, sichtbar als roter Rand an der Card.
- Blocker-Aufloesung: Button `Blockierung aufheben` -> wechselt zu `planned` oder `ready`.
- Drei visuelle Gruppen im Tab-Layout: `Aktiv` (gruen), `Wartet` (gelb: write_back + rating), `Blockiert` (rot).

## Sprint 3 - Grafik als echte Steueroberflaeche #sprint-workflow-visual-control
Goal: Die Grafik soll nicht nur visualisieren, sondern steuerbar und aussagekraeftig sein.

### Interaktive Knoten mit Detail-Drawer #spec-graph-interactions
- Klick auf einen Knoten oeffnet einen echten Detail-Drawer statt nur Scroll-Verhalten.
- Der Drawer zeigt Status, Beschreibung, letzte Session, offene Aktionen, Rating-Zustand und Blocker-Info.
- Von dort aus muessen echte Workflow-Aktionen ausloesbar sein.

**GUI/UX-Spec:**
- Drawer: rechts einfahrendes Panel (400px breit), per `transform: translateX` animiert.
- Drawer-Header: Marker-Titel + Status-Badge + Close-Button (nutzt `closeModal()`-Pattern aus `base.js`).
- Drawer-Body: 4 Sektionen — `Status & Owner`, `Beschreibung/Ziel`, `Letzte Session` (Link), `Aktionen` (gleiche Buttons wie in Sprint 2).
- SVG-Knoten: `cursor: pointer`, Hover-Effekt (leichter Glow via CSS `filter: drop-shadow`).
- Aktiver Knoten pulsiert dezent (CSS `@keyframes pulse-glow`, nicht `animation` auf SVG direkt).
- Drawer schliesst bei Escape und Overlay-Click (via bestehendes Modal-System).

### Fortschritt in der Grafik abbilden #spec-graph-progress
- Zeige echten Fortschritt je Projekt: erledigte Marker, aktive Marker, blockierte Marker, offene Ratings.
- Mache sichtbar, warum ein Schritt stockt.
- Die Grafik soll den Unterschied zwischen `kein Marker`, `bereit`, `in Arbeit`, `wartet auf Rueckschreiben`, `wartet auf Rating` klar zeigen.

**GUI/UX-Spec:**
- Progress-Ring im Zentrum der SVG-Grafik: `done/total` als Kreissegment mit Prozentzahl.
- Knotenfarben aus CSS-Variablen (Dark-Theme-kompatibel): `--wf-planned: #6b7280`, `--wf-ready: #3b82f6`, `--wf-active: #22c55e`, `--wf-write-back: #f59e0b`, `--wf-rating: #eab308`, `--wf-done: #10b981`, `--wf-blocked: #ef4444`.
- Stockender Schritt: oranges Warnsymbol (SVG `⚠`) am Knoten, Tooltip mit Grund.
- Kompakte Zaehlerleiste unter der Grafik: `3 erledigt · 1 aktiv · 1 blockiert · 2 offen`.

### Legende und Bedienlogik #spec-graph-understanding
- Ergaenze eine kleine Legende oder kontextuelle Erklaerung fuer Farben und Status.
- Mache sichtbar, welche Elemente nur Information sind und welche klickbare Aktionen ausloesen.
- Beseitige alle Stellen, an denen der Workflow wie ein Mockup wirkt.

**GUI/UX-Spec:**
- Legende als kompakte horizontale Zeile unter der Zaehlerleiste: farbiger Punkt + Label pro Status.
- Klickbare Elemente bekommen ein subtiles `→`-Icon oder Underline-on-Hover.
- Tooltip auf jedem Knoten: „Klicken fuer Details" (nur wenn Drawer verfuegbar).
- Entferne alle `placeholder`/`coming-soon` Texte aus der bestehenden Grafik.

## Sprint 4 - Rueckkopplung aus operativer Arbeit #sprint-workflow-sync
Goal: Arbeit in Copilot und Sessions muss automatisch im Workflow sichtbar werden.

### Session-Rueckkanal in Marker-Status #spec-session-sync
- Wenn operative Arbeit in Copilot oder Session-Historie passiert, soll der Workflow-Status automatisch aktualisiert werden.
- `last_session`, Arbeitsdauer, Outcome und Abschlussqualitaet muessen sauber ruecklaufen.
- Vermeide manuelle Doppelpflege zwischen Session, Marker und Workflow.

**GUI/UX-Spec:**
- Kein eigenes UI noetig — Sync laeuft im Backend (`_sync_markers_to_workflow` im Loop-Abruf, bereits in Sprint 1 implementiert).
- Session-Link in Marker-Card zeigt automatisch die letzte Session mit Zeitstempel.
- Badge „Letzte Aktivitaet: vor X Stunden" in der Card, berechnet aus `last_transition_at`.

### Copilot- und Workflow-Zustand verbinden #spec-copilot-workflow-link
- Copilot muss wissen, aus welchem Workflow-Schritt die Arbeit gestartet wurde.
- Nach Abschluss muss der Workflow erkennen, ob Write-back und Rating noch fehlen.
- Der Nutzer soll nach Rueckkehr aus Copilot wieder im passenden Workflow-Kontext landen.

**GUI/UX-Spec:**
- Copilot-Board erhaelt kleines Workflow-Status-Badge oben rechts (aktueller Step aus `workflow_states`).
- „Zurueck zum Workflow"-Link im Copilot-Header, fuehrt auf `/project/<name>?tab=workflow&marker=<id>`.
- Workflow-Tab scrollt bei `?marker=<id>` automatisch zur entsprechenden Card und oeffnet den Drawer.
- Nach Copilot-Abschluss: Banner im Workflow-Tab „Letzte Execution abgeschlossen — Write-back und Rating ausstehend".

### Auditierbare Timeline #spec-workflow-timeline
- Zeige eine kleine Verlaufsspur pro Marker: gestartet, bearbeitet, blockiert, abgeschlossen, bewertet.
- Damit wird der Workflow nachvollziehbar und review-faehig.

**GUI/UX-Spec:**
- Timeline als vertikale Linie mit Dots im Detail-Drawer (unterhalb der Aktionen-Sektion).
- Jeder Eintrag: Zeitstempel + `from -> to` Status-Badge + Trigger (`user`/`sync`) + optionaler Reason-Text.
- Daten aus `GET .../history` API (Sprint 1, bereits implementiert).
- Max 10 Eintraege sichtbar, „Alle anzeigen"-Link fuer aeltere.
- Kompakte Darstellung: Timestamp links (grau, klein), Status-Badges rechts, Reason darunter.

## Sprint 5 - UX-Haertung und produktionsreife Bedienung #sprint-workflow-ux-hardening
Goal: Der Workflow-Tab soll im Alltag selbsterklaerend, robust und effizient sein.

### Empty, Error und Edge States #spec-workflow-edge-states
- Leere Projekte, mehrere aktive Marker, fehlende Rueckschreibungen und alte offene Ratings sauber behandeln.
- Jeder Zustand braucht klare Sprache und einen sinnvollen naechsten Schritt.
- Die UI darf nie unklar lassen, was gerade zu tun ist.

**GUI/UX-Spec:**
- Empty State (kein Marker): Illustration + „Noch kein Workflow gestartet. Erstelle einen Plan und importiere Marker." + CTA zu Planning-Tab.
- Error State (API-Fehler): Retry-Button + kurze Fehlermeldung, kein leerer Tab.
- Mehrere aktive Marker: gelber Hinweis-Banner „Mehrere Marker gleichzeitig aktiv — nur einer empfohlen".
- Alte Ratings (>7 Tage): dezenter Hinweis „Rating seit X Tagen offen" in der Card.
- Fehlende Write-backs bei `done`: Zaehler im Tab-Header-Badge „2 ausstehend".

### Rollen, Ownership und Review #spec-workflow-ownership
- Sichtbar machen, wer einen Marker bearbeitet oder reviewen soll.
- Ownership muss in Karten, Drawer und Timeline konsistent auftauchen.
- Blockierte oder ueberfaellige Marker muessen auffallen.

**GUI/UX-Spec:**
- Owner-Anzeige: Avatar-Circle (Initial-basiert) + Name in Card-Header und Drawer.
- Kein Owner gesetzt: grauer Platzhalter „Nicht zugewiesen" mit `Uebernehmen`-Link.
- Ueberfaellige Marker (aktiv >48h ohne Session): orangener Rand + „Seit X Tagen keine Aktivitaet".
- Blockierte Marker: roter linker Rand (4px solid), Grund als Inline-Text sichtbar.
- Review-Hinweis bei `rating`-Status: „Review ausstehend" Badge in Card und Tab-Header.

### Schnelle Operativansicht pro Projekt #spec-workflow-operator-view
- Kompakte Ansicht fuer `Was ist gerade aktiv?`, `Was ist blockiert?`, `Was wartet auf Rating?`.
- Diese Sicht soll fuer taegliche Steuerung ausreichen, ohne in Plans oder Sessions springen zu muessen.

**GUI/UX-Spec:**
- Operator-View als kompakter Bereich oberhalb der Detail-Cards (Toggle „Kompakt / Detail").
- Drei Spalten nebeneinander: `Aktiv` (gruen), `Wartet` (gelb), `Blockiert` (rot).
- Jede Spalte: Zaehler + Liste der Marker-Titel als klickbare Links (oeffnen Drawer).
- Wenn alle Marker `done`: gruener Erfolgsbalken „Alle Marker abgeschlossen".
- Keyboard-Navigation: Tab-Taste springt durch Cards, Enter oeffnet Drawer.
- Mobile: Spalten stapeln vertikal, Cards volle Breite.

## Success Criteria
- Workflow-Tab ist nicht mehr nur Anzeige, sondern erlaubt echte operative Steuerung.
- Marker-Zustaende sind persistiert, nachvollziehbar und eindeutig.
- Die Grafik bildet echten Fortschritt und Blockaden verstaendlich ab.
- Copilot, Sessions, Ratings und Marker-Status sind sauber rueckgekoppelt.
- Ein Nutzer versteht ohne Erklaerung, was der aktuelle Zustand ist und was als Naechstes getan werden muss.
