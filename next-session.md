# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-27
> **Status:** Sprint 1 (Metadaten) abgeschlossen, Sprint 2+3 offen
> **Naechste Aufgabe:** Sprint 2 - Git-erweiterte Features implementieren

---

## Naechste Session - Sprint 2: Git-erweiterte Features

### Sprint-Plan
Datei: `~/.claude/plans/jazzy-booping-pascal.md`

### Tasks Sprint 2 (in dieser Reihenfolge)

1. **Aktivitaets-Score** - Commits 7d/30d zaehlen, gewichteter Score, Level (hot/active/moderate/low/inactive), farbiger Dot in Tabelle
   - `services/git_service.py`: `get_activity_score()`
   - `services/project_scanner.py`: in scan_projects()
   - `static/js/dashboard-table.js`: Dot in Aktivitaets-Spalte

2. **Branches-Uebersicht** - Alle Branches mit letzter Aktivitaet, Branch-Count Badge
   - `services/git_service.py`: `get_branches()`
   - Detail-Ansicht: Branch-Liste

3. **Contributors** - Top 3 Contributor mit Commit-Anzahl
   - `services/git_service.py`: `get_contributors()`
   - Nur in Detail-Ansicht

4. **Environment-Infos** - .env.example Keys auslesen
   - `services/description_extractor.py`: `parse_env_example()`
   - Nur in Detail-Ansicht als Code-Badges

5. **Port-Konflikt-Check** - Projekte mit gleichem Port warnen
   - `services/project_scanner.py`: `detect_port_conflicts()`
   - Warn-Badge in Tabelle

### Betroffene Dateien
| Datei | Aenderung |
|-------|-----------|
| `services/git_service.py` | 3 neue Funktionen (Score, Branches, Contributors) |
| `services/project_scanner.py` | Neue Felder + Port-Konflikt-Check |
| `services/description_extractor.py` | parse_env_example() |
| `routes/project_info_routes.py` | Neue Sections (Branches, Contributors, Env) |
| `static/js/dashboard-table.js` | Activity-Dot, Branch-Count Badge, Port-Warn |

---

## Offene Punkte

### Sprint 3 (danach)
- [ ] GitHub-Integration (Stars, Issues, PRs)
- [ ] CI/CD-Status (GitHub Actions)
- [ ] Deployment-Status (Health-Check)
- [ ] Security/Vulnerabilities (npm audit / pip-audit)

### Dateigroessen-Limits (Pre-Commit)
- [ ] `session_routes.py` (583/500 Zeilen) → aufteilen
- [ ] `sessions2.css` (823/400 Zeilen) → aufteilen

### UI-Verbesserungen
- [ ] Verbleibende hardcoded Hex-Farben in CSS
- [ ] Emoji-Icons in JS-generierten Inhalten durch Lucide ersetzen
- [ ] Plans: 3 nicht-zugeordnete Plans manuell zuordnen

### Infrastruktur
- [ ] Docker vs. systemd klaeren
- [ ] Tailwind CDN durch lokalen Build ersetzen (Production)
