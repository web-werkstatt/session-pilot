# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-27
> **Status:** Sprint 1+2 abgeschlossen, Sprint 3 offen
> **Naechste Aufgabe:** Sprint 3 - GitHub-Integration & Security

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

---

## Naechste Session - Sprint 3: GitHub-Integration & Security

### Tasks Sprint 3

1. **GitHub-Integration** - Stars, Issues, PRs von GitHub-Repos anzeigen
   - Neuer Service: `services/github_service.py`
   - API-Anbindung via Token oder public
   - Badges in Tabelle + Detail-Ansicht

2. **CI/CD-Status** - GitHub Actions Status anzeigen
   - Letzter Workflow-Run: success/failure/pending
   - Badge in Tabelle

3. **Deployment-Status** - Health-Check fuer laufende Services
   - HTTP-Check auf konfigurierte URLs
   - Status-Badge in Tabelle

4. **Security/Vulnerabilities** - npm audit / pip-audit Ergebnisse
   - `services/security_scanner.py`
   - Warn-Badge bei bekannten Schwachstellen

---

## Offene Punkte

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
