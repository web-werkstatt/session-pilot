# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-27
> **Status:** Sprint 1+2+3 abgeschlossen
> **Naechste Aufgabe:** Tech-Debt Cleanup + UI-Verbesserungen

---

## Abgeschlossen

### Sprint 1 - Metadaten (Commit ea34b6f)
Version, Lizenz, LOC, Repo-Size, Changelog Erkennung

### Sprint 2 - Git-erweiterte Features (Commit 69d552e)
- **Aktivitaets-Score** - `git_service.py:get_activity_score()`, farbiger Dot in Tabelle
- **Branches** - `git_service.py:get_branches()`, Count-Badge in Tabelle, Liste in Detail
- **Contributors** - `git_service.py:get_contributors()`, Top 3 in Detail-Ansicht
- **Env-Infos** - `description_extractor.py:parse_env_example()`, Code-Badges in Detail
- **Port-Konflikte** - in `project_scanner.py:scan_projects()`, Warn-Badge in Tabelle

### Sprint 3 - GitHub-Integration & Security (Commit 7568784)
- **GitHub-Integration** - `services/github_service.py`, Stars/Forks/Issues/PRs, Token aus Remote-URL
- **CI/CD-Status** - GitHub Actions letzter Workflow-Run, Badge in Tabelle + Detail
- **Health-Checks** - `services/health_check_service.py`, HTTP-Check auf Ports/URLs, Badge in Tabelle + Detail
- **Security-Scanner** - `services/security_scanner.py`, npm audit / pip-audit, On-Demand API `/api/security/<project>`
- **Detail-Sections** - GitHub, Health-Check, Security in `routes/project_info_sections_s3.py`
- 5 GitHub-Repos erkannt (serena 22k★, open-lovable 24k★, Archon 13k★), 27 Health-Checks aktiv

---

## Offene Punkte

### Dateigroessen-Limits (Pre-Commit)
- [ ] `session_routes.py` (583/500 Zeilen) → aufteilen
- [ ] `sessions2.css` (823/400 Zeilen) → aufteilen

### UI-Verbesserungen
- [ ] Verbleibende hardcoded Hex-Farben in CSS durch CSS-Variablen ersetzen
- [ ] Emoji-Icons in JS-generierten Inhalten durch Lucide ersetzen
- [ ] Plans: 3 nicht-zugeordnete Plans manuell zuordnen

### Infrastruktur
- [ ] Docker vs. systemd klaeren
- [ ] Tailwind CDN durch lokalen Build ersetzen (Production)
