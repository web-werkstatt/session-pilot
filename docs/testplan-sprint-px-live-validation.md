# Testplan Sprint PX - Live-Validierung Hashtag-First Markdown Routine

Stand: 2026-04-04
Status: offen

## Ziel

Diesen Testplan nutzen wir, um den im Repo fertig implementierten Sprint PX gegen echte Projekt- und Board-Daten zu validieren.

Geprueft werden:

- Markdown-Tags `#sprint-*` und `#spec-*`
- serverseitige Struktur `Plan -> Sprint -> Spec -> Marker`
- Marker-Backfill in `handoff.md`
- Copilot-Board `Sprint Sections`
- `Sprint -> Marker` Import
- Idempotenz von Migration und Import

## Voraussetzungen

- App laeuft lokal oder auf dem Zielsystem
- ein reales Projekt mit:
  - mindestens einem Plan
  - mindestens einem Sprint mit `#sprint-*`
  - mindestens einer Spec mit `#spec-*`
  - bestehender `handoff.md`
- Zugriff auf Browser und Terminal

## Testdaten

Vor dem Test festhalten:

- Projektname:
- Plan-ID:
- Plan-Datei:
- handoff-Pfad:
- erwartete Sprint-Tags:
- erwartete Spec-Tags:

## Testreihenfolge

### 1. Plan-API Grundcheck

**Ziel:** Sicherstellen, dass der Plan die neue serverseitige Struktur liefert.

**Schritte:**

1. `GET /api/plans/<PLAN_ID>` aufrufen
2. JSON pruefen

**Erwartet:**

- `tagged_sections` ist vorhanden
- jeder erkannte Sprint hat `sprint_tag`
- Specs tragen `spec_tag`
- Marker sind an der richtigen Sprint-/Spec-Stelle enthalten
- keine offensichtlichen Duplikate

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 2. Copilot-Board Sprint Sections

**Ziel:** Sichtpruefung des neuen tag-basierten UI-Pfads.

**Schritte:**

1. `/copilot?plan_id=<PLAN_ID>` oeffnen
2. Bereich `Sprint Sections` pruefen
3. mehrere Section-Cards oeffnen
4. `Source`-Tab pruefen

**Erwartet:**

- richtige Anzahl Sprints sichtbar
- sinnvolle Task-Zahl pro Section
- sinnvolle Spec-Zahl pro Section
- Marker-Chips haengen an der richtigen Section
- `Source` zeigt Sprint-/Spec-/Task-Kontext plausibel
- Marker-Hierarchie zeigt `sprint_tag` und bei Bedarf `spec_tag`

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 3. Marker-API gegen reale Marker

**Ziel:** Pruefen, dass Marker inkl. neuer Hierarchie-Felder sauber ausgeliefert werden.

**Schritte:**

1. `GET /api/copilot/markers?project_id=<PROJEKT>&plan_id=<PLAN_TOKEN_ODER_PLAN_ID>` aufrufen
2. einzelne Marker pruefen

**Erwartet:**

- Marker enthalten `sprint_tag`
- Spec-bezogene Marker enthalten `spec_tag`
- Gate-/Status-Felder bleiben intakt
- keine Regression bei bestehenden Marker-Feldern

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 4. Migration im Check-Modus

**Ziel:** Nur Analyse, ohne Dateien zu veraendern.

**Schritte:**

1. im Projektroot ausfuehren:

```bash
python3 scripts/markdown_tag_migration.py --check --project <PROJEKT_ODER_PFAD> --handoff <HANDOFF_PFAD>
```

2. Ausgabe pruefen

**Erwartet:**

- nur echte fehlende Tags werden gemeldet
- Marker ohne Mapping bekommen sinnvolle Vorschlaege
- bereits korrekte Tags/Felder werden nicht als Problem gemeldet

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 5. Migration im Apply-Modus

**Ziel:** Fehlende Markdown-Tags und konservativ mappbare Marker wirklich schreiben.

**Schritte:**

1. im Projektroot ausfuehren:

```bash
python3 scripts/markdown_tag_migration.py --apply --project <PROJEKT_ODER_PFAD> --handoff <HANDOFF_PFAD>
```

2. geaenderte Markdown-Dateien pruefen
3. `handoff.md` pruefen

**Erwartet:**

- fehlende `#sprint-*` und `#spec-*` werden sauber in Heading-Zeilen geschrieben
- Marker erhalten `sprint_tag`
- `spec_tag` wird nur bei eindeutigem Mapping gesetzt
- keine bereits korrekten Werte werden unnoetig ueberschrieben

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 6. Idempotenz der Migration

**Ziel:** Zweiter Lauf darf keine neuen Aenderungen erzeugen.

**Schritte:**

1. denselben Apply-Befehl sofort erneut ausfuehren

```bash
python3 scripts/markdown_tag_migration.py --apply --project <PROJEKT_ODER_PFAD> --handoff <HANDOFF_PFAD>
```

2. Ausgabe und Dateien pruefen

**Erwartet:**

- keine neuen Markdown-Aenderungen
- keine neuen Marker-Aenderungen
- keine doppelten Tags

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 7. Sprint -> Marker Import

**Ziel:** Reale Marker-Erzeugung oder Aktualisierung aus einem Sprint pruefen.

**Schritte:**

1. im Copilot-Board den Button `Sprint -> Marker` ausloesen
2. danach Marker-Board und `handoff.md` pruefen

**Erwartet:**

- Marker werden erzeugt oder aktualisiert
- keine Duplikate
- Marker erhalten `sprint_tag`
- Spec-bezogene Marker erhalten `spec_tag`
- bestehende Marker bleiben stabil

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 8. Idempotenz von Sprint -> Marker

**Ziel:** Wiederholter Import erzeugt keine doppelten Marker.

**Schritte:**

1. `Sprint -> Marker` direkt erneut ausloesen
2. Marker-Anzahl vor/nachher vergleichen

**Erwartet:**

- keine doppelten Marker
- nur sinnvolle Updates an bestehenden Markern

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 9. Marker-Kontext und Copilot-Kontext

**Ziel:** Sicherstellen, dass Marker-Aktivierung den neuen Hierarchie-Kontext mitnimmt.

**Schritte:**

1. aktivierbaren Marker im Board auf `OK` setzen
2. `marker-context.md` pruefen
3. optional einen Copilot-Chat fuer diesen Marker ausloesen

**Erwartet:**

- `marker-context.md` enthaelt `marker_id`, `plan_id`, `sprint_tag`, `spec_tag`
- der Marker geht auf `in_progress`
- Copilot-Kontext bleibt konsistent

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

### 10. Legacy-/Grenzfall

**Ziel:** Sicherstellen, dass Fallbacks nicht kaputt gegangen sind.

**Mindestens einen Fall testen:**

- Sprint mit `sprint_tag`, aber ohne Specs
- Marker nur mit `sprint_tag`
- ungetaggter Altplan
- Plan mit teilweiser Tag-Abdeckung

**Erwartet:**

- Fallbacks greifen noch
- kein falsches Spec-Mapping
- Board bleibt benutzbar

**Ergebnis:**

- [ ] bestanden
- [ ] fehlgeschlagen

**Notizen:**

---

## Abnahmekriterien

Sprint PX gilt fachlich als live-validiert, wenn:

- [ ] `tagged_sections` fuer reale getaggte Plaene korrekt geliefert werden
- [ ] Board-Mapping sichtbar ueber `sprint_tag` / `spec_tag` funktioniert
- [ ] Migration in `--check` und `--apply` korrekt arbeitet
- [ ] Migration idempotent ist
- [ ] `Sprint -> Marker` idempotent ist
- [ ] Marker-Kontext die Hierarchie-Felder korrekt fuehrt
- [ ] Legacy-Fallbacks nicht regressiv wirken

## Offene Befunde

- Befund 1:
- Befund 2:
- Befund 3:

## Abschluss

Datum:

Tester:

Status:

- [ ] komplett bestanden
- [ ] bestanden mit Restpunkten
- [ ] nicht bestanden
