# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-27
> **Status:** Sprint 1+2+3 + UI-Verbesserungen abgeschlossen
> **Naechste Aufgabe:** Infrastruktur (Docker vs. systemd, Tailwind lokal)

---

## Session 2026-03-27 (Nacht) - UI-Verbesserungen

### Was wurde erledigt
- **CSS-Variablen:** ~30 neue Design-Tokens definiert (Brand, Syntax, Status, Actions) + ~129 hardcoded Hex-Farben in 22 CSS-Dateien durch var(--...) ersetzt
- **Emoji → Lucide:** 12 JS-Dateien migriert (dashboard-table, -modals, -groups, -news, -actions, -ideas, documents, news, vorlagen, project-detail, sessions2, notifications). Python-Routen waren bereits umgestellt. `renderIcon()` Dual-Mode (Emoji+Lucide) vorhanden
- **Plans zugeordnet:** 3 unassigned Plans (Sticky Save Footer, 2FA System, Admin UI Transparenz) → proj_irtours. 0 unassigned verbleibend
- dashboard-misc.js Emojis bewusst beibehalten (dekorative Zitate)

### Betroffene Dateien
| Bereich | Dateien |
|---------|---------|
| Design-Tokens | static/css/design-tokens.css |
| CSS (22 Dateien) | base, components, containers, dependencies(-graph), documents(-extras), features, modals, news, notifications, plans, project-detail, scaffold, session-analysis, session-detail, session-reviews, sessions-list, settings, table, timesheets, vorlagen |
| JS (12 Dateien) | dashboard-table/-modals/-groups/-news/-actions/-ideas/-state, documents, news, vorlagen, project-detail, sessions2, notifications |
| DB | project_plans: 3 Plans auf proj_irtours zugeordnet |

---

## Naechste Session

### Infrastruktur
- [ ] Docker vs. systemd klaeren
- [ ] Tailwind CDN durch lokalen Build ersetzen (Production)

### Hinweise
- GitHub API: Private Repos brauchen gueltigen Token (einige PATs abgelaufen)
- Health-Checks: Viele Projekte mit Port zeigen "down" weil Service nicht laeuft - ggf. nur fuer aktive Container pruefen
- Security: pip-audit nicht installiert auf dem Server (`pip install pip-audit`)
