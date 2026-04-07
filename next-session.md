# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-04-07 (Closeout)
> **Status:** **Feature-Freeze.** Tag `v1.3-final`. Ab sofort Wartungsmodus.
> **Naechste Aufgabe:** Keine. Dashboard ist stabil und einsatzbereit fuer echte Projekt-Arbeit.

---

## Was gilt jetzt

Das Dashboard ist mit Tag **`v1.3-final`** auf Feature-Freeze gesetzt. Hintergrund:
Sprint SB (Session-Marker-Binding) war der letzte aktive Feature-Sprint. Danach wurde
ein Closeout-Audit durchgefuehrt der ergab: die naechste Welle von Features (Sprint
QS, 12-Voll, 13-Voll, 14, 15, 16, 6, 8, Audit-Erweiterung, 20) braucht ~275-355h
Restaufwand und liefert keinen unmittelbaren Wert fuer die echten Projekte ab Montag.
Diese Sprints sind bewusst verschoben ("Bezahl-Features"), nicht vergessen — siehe
Master-Plan-Block "Deferred Sprints (post-closeout v1.3-final)".

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

- **2026-04-07 vormittags:** Sprint SB DONE (Session-Marker-Binding hart in DB), Tag-Commit `0bac136`
- **2026-04-07 nachmittags:** Closeout durchgefuehrt (M1-M14), Tag `v1.3-final`
- **Davor:** siehe `master-plan-2026-04-01.md` Section "Completed Sprints"
