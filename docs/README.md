# SessionPilot - Dokumentation

**Pfad:** `/mnt/projects/project_dashboard/docs/`
**Stand:** 31. Maerz 2026

---

## Uebersicht

SessionPilot ist ein selbst-gehostetes Dashboard zur Verwaltung und Analyse von AI-Coding-Sessions. Laeuft als Flask-App auf Port 5055.

## Dokumente

| Dokument | Beschreibung |
|----------|-------------|
| [SEITEN-UEBERSICHT.md](SEITEN-UEBERSICHT.md) | Alle Seiten mit URL, Zweck und Features |
| [ARCHITEKTUR.md](ARCHITEKTUR.md) | Backend-Struktur, Services, Datenfluss |
| [API-REFERENZ.md](API-REFERENZ.md) | Alle API-Endpoints mit Parametern |
| [DATENBANK.md](DATENBANK.md) | Tabellen, Spalten, Materialized Views |
| [SPRINT-HISTORIE.md](SPRINT-HISTORIE.md) | Was in welchem Sprint gebaut wurde |

## Schnellstart

```bash
# Entwicklung
python3 app.py

# Produktion
sudo systemctl restart project-dashboard

# Logs
tail -f /mnt/projects/project_dashboard/dashboard.log
```

## Tech-Stack

| Komponente | Technologie |
|-----------|------------|
| Backend | Flask (Python 3.11) |
| Datenbank | PostgreSQL (psycopg2) |
| Frontend | Vanilla JS + Chart.js + Tailwind |
| Icons | Lucide Icons |
| Deployment | systemd Service auf Port 5055 |
| Git | Gitea (git.webideas24.com) + GitHub Mirror |
