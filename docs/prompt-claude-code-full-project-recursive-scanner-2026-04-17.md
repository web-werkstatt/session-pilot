# Prompt fuer Claude Code: Full-Project-Recursive-Scanner reparieren / implementieren

Nutze diesen Prompt in Claude Code fuer die Wiederherstellung des verlorenen
Scanners.

```text
Du arbeitest im Repo `/mnt/projects/project_dashboard`.

Kontext:

- Es gibt bereits einen funktionierenden Multi-Source-Plan-Scanner:
  - `services/plan_discovery_service.py`
  - `services/plans_sync_service.py`
  - `routes/plan_scan_routes.py`
  - `routes/plans_routes.py`
- Dieser vorhandene Scanner scannt nur feste Quellen:
  - `~/.claude/plans/`
  - `<project>/sprints/`
  - `<project>/plans/`
  - `<project>/docs/{plans,sprints}/`
  - `<project>/{roadmap,ROADMAP,MASTERPLAN,master-plan}.md`
- Er ist NICHT der gesuchte zweite Scanner.
- Gesucht ist ein zusaetzlicher Full-Project-Recursive-Scanner, der
  planartige Markdown-Dateien auch ausserhalb dieser Standardpfade in
  `/mnt/projects/<projekt>/...` findet und ueber die bestehende Sync-/Upsert-
  Logik in `project_plans` importiert.
- Diese Arbeit wurde laut User am 2026-04-16 bereits begonnen, ist aber im
  aktuellen Repo-Stand nicht mehr direkt auffindbar und muss rekonstruiert
  werden.

Wichtige Referenzen:

- `docs/full-project-recursive-scanner-recovery-2026-04-17.md`
- `sprints/sprint-full-project-recursive-plan-scanner.md`
- `services/plan_discovery_service.py`
- `services/plans_sync_service.py`
- `services/project_scanner.py`
- `services/metadata_extractor.py`
- `tests/test_plan_discovery.py`

Dein Auftrag:

1. Lies zuerst:
   - `docs/full-project-recursive-scanner-recovery-2026-04-17.md`
   - `sprints/sprint-full-project-recursive-plan-scanner.md`
   - `services/plan_discovery_service.py`
   - `services/plans_sync_service.py`

2. Implementiere den verlorenen Scanner als Erweiterung des bestehenden
   Discovery-/Sync-Stacks, nicht als komplett neues paralleles System.

3. Zielzustand:
   - rekursive Discovery unter `/mnt/projects/<projekt>/...`
   - nur fuer `.md`-Dateien
   - nur fuer planartige Dateien gemaess bestehender Heuristik
   - Standardpfade (`sprints/`, `plans/`, `docs/plans`, `docs/sprints`,
     Root-Roadmaps) duerfen NICHT als `project_recursive` doppelt auftauchen
   - rekursive Funde erhalten `source_kind='project_recursive'`
   - Import laeuft ueber bestehende `sync_all_plans()`-Logik
   - API / UI sollen diese Quelle sichtbar machen

4. Halte dich an diese Leitplanken:
   - keine destruktiven Git-Befehle
   - keine bestehende Upsert-Logik neu erfinden
   - `project_name` weiter aus dem Pfad ableiten
   - `source_path` bleibt kanonischer `realpath`
   - bestehende Blacklists, Groessenlimits, Cooldown, Circuit-Breaker und
     Notification-Suppression beibehalten

5. Sinnvolle technische Umsetzung:
   - `services/plan_discovery_service.py` erweitern
   - falls noetig Hilfsfunktion bauen, die pro Projekt rekursiv scannt
   - bekannte Standardpfade explizit vom rekursiven Pfad ausschliessen
   - `routes/plans_routes.py` / `routes/plan_scan_routes.py` / `static/js/plans.js`
     fuer `project_recursive` ergaenzen
   - Test-Stubs oder Verifikationsfaelle fuer rekursive Funde ergaenzen

6. Akzeptanzkriterien:
   - Datei ausserhalb Standardpfad wird gefunden und importiert
   - Datei unter Standardpfad wird nicht doppelt als `project_recursive`
     aufgenommen
   - `source_kind='project_recursive'` ist in API/UI sichtbar
   - zweiter Sync aktualisiert statt zu duplizieren
   - Python/JS-Syntaxchecks laufen durch

7. Verifikation nach Implementierung:
   - `python3 -m py_compile services/*.py routes/*.py`
   - `node --check static/js/plans.js`
   - `node --check static/js/plan_scan_panel.js`
   - beschreibe kurz, wie du den rekursiven Fall manuell getestet hast

8. Dokumentation:
   - aktualisiere `next-session.md`
   - wenn die Arbeit abgeschlossen ist, dokumentiere den Sprint in
     `sprints/master-plan-2026-04-01.md`

Arbeite direkt im Repo und implementiere die Aenderungen, nicht nur analysieren.
```
