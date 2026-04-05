# Next Session Archive 2026-04-05

Archivierte Inhalte aus `next-session.md`, nachdem die Datei auf einen Minimal-Handoff reduziert wurde.

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
- Betroffene Dateien: `copilot_board.html`, `copilot.css`, `copilot_board.js`, `copilot_routes.py`, `copilot_landing.html`, `copilot_landing.css`
- Zuruecksetzen und dann sauber neu anfangen

### Offene Aufgaben (aus vorheriger Session)
- [ ] Copilot-Workflow: Perplexity als Copilot einsetzen
- [ ] LLM-agnostischer Connector (`llm_connector.py`)
- [ ] Pre-Commit Zeilenlimits fixen (`db_service.py` 526Z, `governance_service.py` 519Z)
- [ ] 6x `bare except` fixen
- [ ] 5x f-strings ohne Platzhalter (`F541`)
- [ ] 7x unused global declarations (`F824`)

### Nicht vergessen
- Referenzbild: `upload/ChatGPT Image 3. Apr. 2026, 11_49_55.png`
- Release-Skill: `sessionpilot-release`
- Level-Architektur: `/plans` = Level 1, `/copilot?plan_id=X` = Level 2
- Handoff-Service: `project_handoff_service.py`
- User-Erwartung: professionell, reduziert, dark, elegant; keine Marketing-UI, keine generische Kanban-Optik

## Update 2026-04-05
- Changed: Den restlichen Copilot-/Markdown-Block modular repo-faehig gemacht; Marker-APIs aus `routes/copilot_routes.py` in `routes/copilot_marker_routes.py` ausgelagert, `services/copilot_marker_service.py` in Format-/Import-/Runtime-Module getrennt, das Copilot-Board in `shared + board + panel` JS-Dateien aufgeteilt und die grossen Copilot-Tests in mehrere kleinere Suites zerlegt, damit alle geaenderten Dateien unter der 500-Zeilen-Grenze bleiben.
- Files: `routes/__init__.py`, `routes/copilot_routes.py`, `routes/copilot_marker_routes.py`, `services/copilot_marker_service.py`, `services/copilot_marker_format.py`, `services/copilot_marker_import_flow.py`, `templates/copilot_board.html`, `static/js/copilot-board-shared.js`, `static/js/copilot_board.js`, `static/js/copilot-board-panel.js`, `tests/test_copilot_core.py`, `tests/test_copilot_marker_activation_routes.py`, `tests/test_copilot_marker_api_routes.py`, `tests/test_copilot_marker_service_core.py`, `tests/test_copilot_marker_service_flow.py`
- Verify: `python3 -m py_compile routes/copilot_routes.py routes/copilot_marker_routes.py services/copilot_marker_service.py services/copilot_marker_format.py services/copilot_marker_import_flow.py tests/test_copilot_core.py tests/test_copilot_marker_activation_routes.py tests/test_copilot_marker_api_routes.py tests/test_copilot_marker_service_core.py tests/test_copilot_marker_service_flow.py`, `node --check static/js/copilot-board-shared.js`, `node --check static/js/copilot_board.js`, `node --check static/js/copilot-board-panel.js`, `pytest tests/test_copilot_core.py tests/test_copilot_marker_activation_routes.py tests/test_copilot_marker_api_routes.py tests/test_copilot_marker_service_core.py tests/test_copilot_marker_service_flow.py tests/test_markdown_routine_service.py tests/test_markdown_tag_migration.py tests/test_marker_workflow_consistency.py -q`
- Next: Browser-/Live-Validierung fuer den modularisierten Copilot-Flow gegen echte Plaene und danach Session 4 von Sprint QR fuer die Session-Zuordnung an `Task`/`Spec`
