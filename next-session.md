# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-28
> **Status:** Fetch-Wrapper implementiert, alle JS-Dateien migriert
> **Naechste Aufgabe:** Quality Pipeline starten (Sprint 5)

---

## Session 2026-03-28 (Nacht) - Zentraler Fetch-Wrapper + CSS-Fix

### Was wurde erledigt

**Fetch-Wrapper `api.js`:**
- Neues Modul `static/js/api.js` als zentrale HTTP-Schicht
- ~85 rohe fetch()-Aufrufe in 24 JS-Dateien auf api.get/post/put/del umgestellt
- Automatisches JSON-Parsing, Content-Type-Header, Status-Check
- ApiError-Klasse mit status, body, message
- Convenience-Methoden: get, post, put, patch, del, request (raw fuer Downloads)
- Eingebunden in base.html vor base.js

**CSS-Fix:**
- `sessions-list.css` und `session-reviews.css` aus Git-History wiederhergestellt
- Waren in b0a5cd7 faelschlicherweise als "verwaist" geloescht worden
- Werden per @import in sessions2.css eingebunden

### Betroffene Dateien
| Datei | Aenderung |
|-------|-----------|
| `static/js/api.js` | NEU - Zentraler Fetch-Wrapper |
| `templates/base.html` | api.js Script-Tag eingefuegt |
| `static/js/*.js` (24 Dateien) | fetch() -> api.* migriert |
| `static/css/sessions-list.css` | Wiederhergestellt aus Git |
| `static/css/session-reviews.css` | Wiederhergestellt aus Git |

---

## Naechste Session

### Aufgaben
- [ ] Quality Pipeline: Sprint 5 - Package + Scanner (auto_coder)
- [ ] CLAUDE.md aktualisieren: api.js Pattern dokumentieren

### Offene Punkte
- project_scanner.py vs project_detector.py: Tag-Erkennung teilweise dupliziert

### Referenz
- Sprint-Plan Quality: `sprints/sprint-5-scanner.md`
- Quality Roadmap: `sprints/05-roadmap-quality-pipeline.md`
