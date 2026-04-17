---
name: project-dashboard-context-routing
description: Verwende dieses Skill, wenn du im Repo `project_dashboard` arbeitest und den aktuellen Arbeitskontext, die operative Priorität und die richtige Quellenhierarchie aus den bereinigten Handoff- und Sprint-Dateien ableiten musst.
---

# Project Dashboard Context Routing

## Ziel

Dieses Skill verhindert, dass Codex oder andere Agenten aus veralteten
Chronik-Blöcken, Archivtexten oder überholten Sprint-Ständen arbeiten.

Es definiert die gültige Quellenhierarchie für dieses Repo und verweist auf
eine kompakte Session-Referenz, damit der aktuelle Stand nicht jedes Mal neu
rekonstruiert werden muss.

## Wann verwenden

- Bei jeder neuen Session im Repo `project_dashboard`
- Wenn unklar ist, welche `.md`-Datei gerade führend ist
- Wenn alte Session-Blöcke, Archivdateien oder der Master-Plan im Widerspruch
  zu `next-session.md` oder `NOW-next-critical-path.md` zu stehen scheinen
- Wenn eine Aufgabe im Umfeld von Handoff, Sprint-Planung, Recovery,
  Scanner-Abnahme oder Agent-Orchestrator bearbeitet wird

## Quellenhierarchie

Arbeite in genau dieser Reihenfolge:

1. `next-session.md`
   - nur als aktueller Kurz-Handoff
   - enthält Status, nächste Aufgabe, operative Hinweise
   - nicht als Langchronik lesen

2. `sprints/NOW-next-critical-path.md`
   - primäre operative Prioritätsdatei
   - bestimmt `NOW`, `NEXT`, `LATER`

3. passende Sprint-Datei zur Aufgabe
   - Agent-Orchestrator Phase 1:
     `sprints/sprint-agent-orchestrator-phase-1-foundation.md`
   - Resolver / Gesamtpfad:
     `sprints/sprint-agent-orchestrator-5-day-execution-plan.md`
   - technische Details:
     `docs/agent-orchestrator-hardening-technical-spec.md`
   - historische Scanner-Einordnung:
     `sprints/sprint-full-project-recursive-plan-scanner.md`

4. historische Einordnung nur bei Bedarf
   - `sprints/master-plan-2026-04-01.md`
   - `docs/next-session-archive-2026-04-05.md`

## Harte Regeln

- Leite keine aktuelle Priorität aus dem Archiv ab.
- Leite keine unmittelbare Aufgabe aus alten Session-Blöcken im Master-Plan ab.
- Behandle `next-session.md` als operative Wahrheit, nicht als Geschichtsbuch.
- Wenn `next-session.md` und Archivtext sich widersprechen, gilt
  `next-session.md`.
- Wenn `NOW-next-critical-path.md` und ältere Sprint-Notizen sich
  widersprechen, gilt `NOW-next-critical-path.md`.

## Aktueller Repo-Stand

Der `project_recursive`-Scanner ist abgeschlossen:

- live verifiziert
- bereinigt
- dokumentiert

Er ist **kein** Default-Fokus mehr.

Der aktuelle Arbeitsfokus ist:

1. Agent-Orchestrator Phase 1
2. Handoff-/Marker-Resolver

Scanner-Tuning ist nur noch Follow-up bei echtem Bedarf.

## Sofortkontext dieser Session

Lies für den kompakten Stand dieser Session:

- `codex-skills/project-dashboard-context-routing/references/session-2026-04-17.md`

Diese Referenz enthält:

- was in dieser Session bereinigt wurde
- welche neuen `.md`-Dateien jetzt führend sind
- was abgeschlossen ist
- was bewusst nicht mehr auf dem Critical Path liegt

## Arbeitsweise

Wenn du eine neue Aufgabe übernimmst:

1. Lies `next-session.md`
2. Lies `sprints/NOW-next-critical-path.md`
3. Lies die thematisch passende Sprint-Datei
4. Lies die Session-Referenz nur ergänzend
5. Greife erst danach zu Archiv oder Master-Plan

## Nicht tun

- Nicht zuerst `master-plan-2026-04-01.md` lesen, um die nächste Aufgabe zu
  bestimmen
- Nicht aus `docs/next-session-archive-2026-04-05.md` operativ arbeiten
- Nicht den Recursive-Scanner wieder als Hauptbaustelle behandeln
- Nicht neue Meta-Sprints aufmachen, solange Phase 1 und Resolver offen sind

## Update-Block-Format für `next-session.md`

`next-session.md` ist **Kurz-Handoff**, nicht Chronik. Wenn nach erledigter
Arbeit ein Update-Block angehängt wird, gilt:

### Pflichtformat

```
## Update <YYYY-MM-DD> — <ein Satz, was erledigt wurde>
- Changed: 1–2 Sätze, keine Changelog-Auflistung
- Files: Bullet-Liste, nur die wirklich geänderten Pfade, keine Kommentare
- Verify: nur echte Belege (Command → Ergebnis), keine Wiederholung des Sprint-Nachtrags
- Next: 1 Satz, was als Nächstes ansteht (Referenz auf NOW-next-critical-path.md)
```

### Regeln

- Ziel-Länge: **max ~10 Zeilen pro Update-Block**.
- Details (Tabellen, Modulübersichten, Akzeptanz-Kreuze, komplette
  Commit-Listen) gehören in den `## Nachtrag <Datum>`-Block der passenden
  Sprint-Datei, **nicht** in `next-session.md`.
- Wenn beide Dateien dasselbe beschreiben: `next-session.md` **verweist** auf
  den Sprint-Nachtrag, wiederholt ihn nicht.
- Append-only bleibt **ausserhalb** des `DASHBOARD-GENERATED`-Blocks
  (`source=session-handoff`). Der Kopfbereich (Status-Zitat, "Was gilt
  jetzt", NOW/NEXT/LATER/DONE) darf und soll nach erledigter Arbeit
  überschrieben werden, damit die Prioritäten aktuell bleiben. Alles unterhalb
  des Blocks (Bestand-Tabelle, Update-Chronik, operative Hinweise) bleibt
  append-only.
- Semantik der Listen im generierten Block:
  - `### NOW`: genau eine aktuell anliegende Aufgabe. Bei Sessionende auf die
    Nachfolge-Aufgabe umziehen.
  - `### NEXT`: 1–3 Punkte direkt nach NOW, nicht kumulativ.
  - `### LATER`: Rest-Scope, selten angefasst, aber überschreibbar wenn sich
    Prioritäten ändern.
  - `### DONE (diese Session)`: nur die aktuell abgeschlossene Session, nicht
    kumulativ. Historische DONEs gehören in die `## Was funktioniert
    (= Bestand)`-Tabelle oder in Update-Block + Sprint-Nachtrag.
- Keine Emojis, keine Markdown-Ornamente.

### Gilt genauso fuer `sprints/NOW-next-critical-path.md`

- Kopfbereich (Zweck, NOW, NEXT, LATER, DONE) ist in
  `<!-- DASHBOARD-GENERATED:START source=critical-path --> ... :END -->`
  gewrappt und wird nach erledigter Arbeit überschrieben.
- Alles unterhalb des Blocks ("Nicht jetzt", "Abbruchregel", "Nachtrag ...")
  bleibt append-only.
- `next-session.md` und `NOW-next-critical-path.md` müssen inhaltlich
  konsistent bleiben: Was in `next-session.md` NOW steht, ist auch in
  `NOW-next-critical-path.md` NOW.

### Reine Execution-Pläne

Sprint-Dateien wie `sprint-agent-orchestrator-5-day-execution-plan.md` bleiben
vollständig append-only. Tages- oder Etappenstatus wird nur über
`## Nachtrag <Datum>`-Blöcke mit DONE/OPEN-Markierungen nachgezogen, nicht
durch generierte Kopfbereiche.

### Gegenbeispiele (vermeiden)

- Ausführliche File-Kommentare pro Datei im `Files:`-Block.
- `Verify:` mit Commands UND Ergebnissen UND Akzeptanz-Kreuzen.
- Wiederholung der Modul-Struktur oder Architektur-Entscheidung aus dem
  Sprint-Nachtrag.
- „Was funktioniert / Bestand"-Tabellen am Sessionende erneut anfügen.
