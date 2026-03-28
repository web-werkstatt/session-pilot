# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-28
> **Status:** Sprint 6 System Cleanup + Code Quality abgeschlossen
> **Naechste Aufgabe:** Modal-Handling vereinheitlichen, dann Quality Pipeline fortsetzen

---

## Session 2026-03-28 (Nachmittag) - System Cleanup + Code Quality

### Was wurde erledigt

**Performance & Sync:**
- Session-Sync Timer deaktiviert (lief alle 20 Min, 485s pro Lauf)
- Hash-basierter Cache (.sync_hashes.json) - Sync jetzt <1s statt 485s
- Auto-Sync bei Sessions-Seitenaufruf mit 1h Cooldown
- JSONL-Import Escape-Fehler behoben (\u0000, \x00 in content_json)

**DB-Bereinigung:**
- messages-Tabelle von 11 GB auf 713 MB reduziert
- 4.4 Mio duplizierte Messages entfernt (Bug: DELETE vor INSERT fehlte)
- NoneType-Absicherung bei Session-INSERT

**System-Bereinigung:**
- 20 Docker Container gestoppt, ~300 GB Docker-Muell freigegeben
- Ollama, PCP, docker-mec-autostart deaktiviert

**Code Cleanup:**
- 4 verwaiste Dateien geloescht (context_tracker.py, dashboard.js, 2x CSS)
- 2 ungenutzte Funktionen entfernt
- session_import_utils.py: Shared Helpers extrahiert (parse_ts, sanitize_content_json)
- Python-Duplikate: _build_timesheet_filter(), _parse_search_output()
- JS-Duplikate: formatTokens/formatDate/formatDateTime nach base.js
- CSS-Duplikate: .empty-state nur noch in components.css
- @api_route Decorator: 22x try/except in 6 Route-Dateien ersetzt
- CLAUDE.md mit allen neuen Patterns aktualisiert

### Git Commits
```
7a7b473 refactor: Zentrales Error-Handling via @api_route Decorator
3d5cf9c refactor: Doppelte Funktionen konsolidiert
b0a5cd7 refactor: Verwaisten Code entfernt, Duplikate bereinigt
3692454 fix: NoneType-Absicherung bei Session-INSERT mit ON CONFLICT
81a39fd fix: Message-Duplikat-Bug und \u0000 Escape-Fehler behoben
1b866d8 fix: JSONL-Import Escape-Fehler bei content_json behoben
5db605e fix: Auto-Sync bei Sessions-Seitenaufruf statt manueller Trigger
13a78eb fix: Session-Sync durch Hash-Cache optimiert, Timer entfernt, fixes #5
```

---

## Naechste Session

### Aufgaben
- [ ] Modal-Handling vereinheitlichen (generische openModal/closeModal in base.js)
  - 8+ verschiedene Implementierungen, teils classList, teils style.display
  - Mehrere closeModal() mit identischem Namen in verschiedenen Dateien
- [ ] Quality Pipeline fortsetzen (auto_coder Sprint 6: DeRep + Fixer)

### Offene Punkte
- project_scanner.py vs project_detector.py: Tag-Erkennung teilweise dupliziert
- Firewall: ~100 ufw-Regeln fuer inaktive Projekte (Dev-Server, niedrige Prio)

### Referenz
- Sprint-Plan Cleanup: `sprints/sprint-6-system-cleanup.md`
- Sprint-Plan Quality: `sprints/sprint-5-scanner.md`
- GitHub Issue: web-werkstatt/session-pilot#5
