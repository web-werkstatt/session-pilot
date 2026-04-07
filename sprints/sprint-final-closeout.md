# Sprint FINAL — Dashboard Closeout

Stand: 2026-04-07
Status: **DONE 2026-04-07** (umgesetzt als M1-M14 im Closeout)
Ziel-Datum: **heute, 2026-04-07** ✓ erreicht
Tag: `v1.3-final`

> Dieser Plan ist die Konzept-Vorlage. Die tatsaechliche Umsetzung erfolgte
> als M1-M14 (Smoke-Test, Sidebar-Audit, Service/Logs, Backup-Strukturfix,
> Schema-Check, Datei-Aufraeumen, Issue-Triage, Doku-Updates, Master-Plan,
> next-session.md, Week-Final-Plan-Defer, Tag, finaler Smoke-Test). Details
> siehe Closeout-Conversation-Log 2026-04-07.

---

## Scope-Annahme (bitte bestaetigen oder korrigieren)

"Das gesamte Programm abschliessen" = **Feature-Freeze fuer `project_dashboard`**.
Ab morgen liegt der Fokus auf echten Produkt-Projekten; das Dashboard bleibt als
stabiler, dokumentierter Arbeitsstand zurueck.

Das bedeutet ausdruecklich **nicht**:

- alle 10 offenen Sprints (QS, 14, 15, 12, 13, 16, 6, 8, 20, Audit-Weiterentwicklung)
  heute durchziehen — das ist in einem Tag nicht realistisch und kein Feature liefert
  morgen Wert fuer die echten Projekte
- Sprint QS Phase 2/3 (Marker-State DB-first, UI-Entkopplung)
- neue Features, Refactorings "while we're at it"

## Ziel

Am Ende des Tages gilt:

1. Es gibt keine offenen halbfertigen Code-Pfade oder Branches.
2. Dokumentation (README, CLAUDE.md, next-session.md, Master-Plan) spiegelt den
   tatsaechlichen Stand.
3. Betrieb ist abgesichert: Service laeuft, Backups gruen, DB-Schema konsistent.
4. Alle offenen Ideen sind als "deferred" sichtbar markiert — nicht geloescht,
   aber auch nicht als "TODO naechste Session" im Weg.
5. Es existiert ein Release-Tag `v1.x-final` als Markierung des Closeout-Standes.

## Nicht-Ziele

- Sprint QS ueberhaupt anfangen — wird explizit deferred
- Sprint 14/15/12/13/16/6/8/20 — deferred
- Code-Kosmetik, Refactoring, Dependency-Updates ohne konkreten Anlass
- Tests nachtraeglich ergaenzen, wo aktuell keine sind

---

## Arbeitspakete (sequentiell)

### AP1 — Bestandsaufnahme & Branch-Hygiene (30 min)

- `git status`, `git log --oneline -20`, `git branch -a` pruefen
- Sprint SB Commit ist `0bac136` (bereits gepusht) — nichts zu tun
- Unversionierte Dateien pruefen: `.codex/`, `marker-context.md`, `static/uploads/`
  - Entscheidung pro Datei: commit, gitignore oder loeschen (mit Rueckfrage bei Unklarheit)
- Offene Gitea-Issues checken: `gh`/curl auf `git.webideas24.com/.../issues`
  - Jedes offene Issue: entweder schliessen mit Begruendung oder als "deferred, post-closeout" labeln

**Akzeptanz:** `git status` ist sauber oder alle offenen Dateien sind bewusst ignoriert.

---

### AP2 — Dokumentations-Snapshot (45 min)

**README.md** — pruefen ob es das Dashboard akkurat beschreibt:
- Features-Liste aktuell? (Sprint SB, alle P3.x, Audit, Copilot-Board)
- Installations-Anweisung funktioniert? (setup.sh + docker-compose Pfade)
- Screenshots noch gueltig? (nur vermerken, nicht neu erstellen)

**CLAUDE.md** — bereits hochaktuell (Session-Marker-Binding dokumentiert).
- Abschnitt "Wichtige Patterns" ueberfliegen, nichts veraltetes drin lassen
- Keine Aenderungen erwartet

**sprints/master-plan-2026-04-01.md**:
- Abschnitt "Open / Next Sprints" umbenennen zu "Deferred Sprints (post-closeout)"
- Kurzer Header-Block: "Dashboard feature-frozen 2026-04-07. Diese Sprints bleiben
  dokumentiert als Ideen-Pool fuer eventuelle spaetere Iterationen."

**next-session.md** — komplett neu schreiben:
- Titel: "Dashboard Closeout — 2026-04-07"
- Inhalt: "Feature-Freeze. Keine aktive Weiterentwicklung. Bei Bedarf an einem der
  deferred Sprints: master-plan lesen, daraus neuen Sprint-Plan in `sprints/` erzeugen,
  Closeout-Tag als Basis verwenden."

**Akzeptanz:** Ein Aussenstehender (oder zukuenftiges-Ich) versteht in 5 Minuten
warum das Dashboard jetzt frozen ist und wie er einen deferred Sprint reaktivieren wuerde.

---

### AP3 — Betrieb & Datenintegritaet (45 min)

- `sudo systemctl status project-dashboard` — Service active
- `sudo journalctl -u project-dashboard --since today` — keine Fehler-Spam
- Backup-Lauf pruefen: `ls -la /mnt/projects/backups/project-dashboard/`
  - Letztes Backup <24h alt
  - Stichprobe: ein Backup-Archiv entpacken, JSON-Dateien lesen koennen
- DB-Schema-Konsistenz ueber Service-Layer:
  - Alle `ensure_*_schema` Funktionen einmal durchlaufen lassen (z.B. via kurzem
    Service-Restart, der beim Request die Lazy-Schemas zieht)
  - `/api/data`, `/api/sessions`, `/api/markers/<id>/sessions` je ein Smoke-Test
- Scheduled Tasks / RemoteTrigger kurz auflisten, keine broken Trigger

**Akzeptanz:** Service laeuft gruen, Backup frisch und lesbar, API-Smoke-Tests 200 OK.

---

### AP4 — Offene Arbeitsartefakte aufraeumen (30 min)

- `marker-context.md` (im Root, unversioniert): ist das noch aktiver Arbeitskontext?
  - Wenn nein: in `sprints/archive/` verschieben oder loeschen (Rueckfrage)
- `static/uploads/` durchsehen: nur produktive Uploads, keine Test-Muell-Dateien
- `.codex/` pruefen — gehoert in `.gitignore`?
- `sprints/`-Ordner: gibt es halbfertige Sprint-Plan-Dateien ohne Status?
  - Jede Sprint-Datei hat klaren Status-Header (Done / Deferred / Frozen)

**Akzeptanz:** Kein halbgarer Sprint-Plan ohne Status, keine Uploads-Leichen.

---

### AP5 — Release-Tag & Commit (15 min)

- Alle Aenderungen aus AP1-AP4 committen:
  `docs: dashboard feature-freeze + closeout (refs #NN)`
- Gitea-Issue "Dashboard Closeout" vorher erstellen, im Commit referenzieren
- Git-Tag: `git tag -a v1.3-final -m "Dashboard feature-freeze 2026-04-07"`
- Push zu Gitea: `git push && git push --tags`
- GitHub-Mirror **nur nach Rueckfrage** (global rule: Verkaufsschutz)
- Service ein letztes Mal restarten und Smoke-Test

**Akzeptanz:** Tag `v1.3-final` auf Gitea sichtbar, Service gruen, Commit referenziert
das Closeout-Issue.

---

## Zeitbudget

| AP | Dauer | Kumuliert |
|----|-------|-----------|
| AP1 Branch-Hygiene | 0:30 | 0:30 |
| AP2 Dokumentation | 0:45 | 1:15 |
| AP3 Betrieb | 0:45 | 2:00 |
| AP4 Artefakte | 0:30 | 2:30 |
| AP5 Tag & Commit | 0:15 | 2:45 |

**Gesamt: ca. 2h 45min.** Puffer fuer unerwartete Funde: weitere 1-1.5h.
Realistischer Abschluss: **4-5 Stunden netto**, passt in einen Tag.

---

## Abbruchkriterien

Wenn in AP1-AP3 ein echtes Produktproblem auftaucht (Service crashed, DB inkonsistent,
Backup korrupt), wird der Closeout gestoppt und stattdessen das Problem gefixt.
Feature-Freeze bedeutet nicht Bugs-Freeze.

## Deferred (explizit, damit sichtbar)

Folgende Sprints aus dem Master-Plan werden nach dem Closeout **nicht** bearbeitet
und bleiben als dokumentierter Ideen-Pool stehen:

- Sprint QS — DB-First State Consolidation (alle 3 Phasen)
- Sprint 14 — Sprint-Flow-Tracking
- Sprint 15 — Turn-Level-Rating
- Sprint 12 — Governance Feedback-Loop (Voll-Version)
- Sprint 13 — Bidirektionaler LLM-Control (Voll-Version)
- Sprint 16 — Workflow-Profiles
- Sprint 6 — DeRep Fixer
- Sprint 8 — Automation Tuning
- Sprint 20 — Product Launch Bundle
- Audit-Weiterentwicklung

Reaktivierung jederzeit moeglich: neuen Sprint-Plan in `sprints/` anlegen, `v1.3-final`
als Ausgangspunkt nutzen.
