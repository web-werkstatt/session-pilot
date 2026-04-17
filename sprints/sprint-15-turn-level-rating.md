# Sprint 15: Turn-Level Rating #sprint-sprint-15-turn-level-rating

**Ziel:** Sessions nicht nur als Ganzes bewerten, sondern einzelne Abschnitte
(Aufgaben/Turns) innerhalb einer Session separat raten. Ergibt praezisere
Fehleranalyse und bessere Daten fuer Rule-Generator und Modellvergleich.
**Abhaengigkeit:** Sprint 9 (Outcome-System), Sprint 12 (Governance/Rules)
**Geschaetzter Umfang:** 1-2 Sessions

---

## Motivation

Eine Claude-Session hat oft 50+ Turns mit verschiedenen Aufgaben:
- Turn 1-15: Feature A implementiert (OK)
- Turn 16-30: Bug B gefixt (Needs Fix - falscher Ansatz)
- Turn 31-50: Refactoring C (OK)

Aktuell bekommt die gesamte Session ein Outcome. "Needs Fix" fuer die ganze
Session verliert die Info, dass 2 von 3 Aufgaben korrekt waren. Das verfaelscht:
- Rework-Rate (zu hoch wenn nur 1 Turn schlecht war)
- Modellvergleich (Modell wird bestraft obwohl es 90% richtig gemacht hat)
- Rule-Generator (kann Fehler nicht dem richtigen Kontext zuordnen)

---

## Aufgaben

### 15.1 Konzept: Was ist ein "Abschnitt"? #spec-15-1-konzept-was-ist-ein-abschnitt

**Definition:** Ein Abschnitt (Segment) ist eine zusammenhaengende Gruppe von
Messages die eine logische Aufgabe behandeln.

**Erkennung (automatisch, heuristisch):**

```python
def detect_segments(messages):
    """Erkennt logische Abschnitte in einer Session.

    Heuristiken:
    1. User-Message nach langer Pause (>5 Min) = neuer Abschnitt
    2. User-Message mit neuem Thema (Keyword-Wechsel) = neuer Abschnitt
    3. Explizite Marker: "Naechste Aufgabe:", "Jetzt:", Slash-Commands
    4. Tool-Wechsel: Von Read/Grep zu Write/Edit = neuer Arbeitsblock
    """
```

**Alternativ (manuell):** User markiert Abschnittsgrenzen in der Session-Detail-UI
per Klick zwischen Messages.

**Empfehlung:** Automatische Erkennung als Default, manuelle Korrektur moeglich.

### 15.2 DB-Schema: Segmente #spec-15-2-db-schema-segmente

```sql
CREATE TABLE session_segments (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES sessions(id) ON DELETE CASCADE,
    segment_index INT NOT NULL,          -- 0-basiert, Reihenfolge
    start_message_id INT REFERENCES messages(id),
    end_message_id INT REFERENCES messages(id),
    start_turn INT,                       -- User-Message-Nummer (1-basiert)
    end_turn INT,

    -- Bewertung
    outcome VARCHAR(20),                  -- ok, needs_fix, reverted, partial, NULL
    outcome_reason VARCHAR(50),
    outcome_severity VARCHAR(20),
    outcome_note TEXT,
    rated_at TIMESTAMPTZ,

    -- Automatisch extrahiert
    summary TEXT,                          -- 1-Zeiler: "Feature A implementiert"
    ai_has_writes BOOLEAN DEFAULT FALSE,
    ai_tools_used JSONB DEFAULT '[]',
    files_touched JSONB DEFAULT '[]',     -- Dateien die in diesem Segment beruehrt wurden
    token_count INT,                      -- Tokens in diesem Segment
    duration_ms INT,                      -- Dauer dieses Segments

    -- Meta
    auto_detected BOOLEAN DEFAULT TRUE,   -- Automatisch erkannt vs. manuell gesetzt
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (session_id, segment_index)
);
```

### 15.3 Segment-Erkennung Service #spec-15-3-segment-erkennung-service

**`services/segment_detector.py` (neu):**

```python
SEGMENT_GAP_MS = 300000  # 5 Minuten Pause = neuer Abschnitt

TOPIC_CHANGE_KEYWORDS = [
    "jetzt", "naechste", "nun", "next", "now", "also",
    "neues feature", "new feature", "bug fix", "refactor",
]

def detect_segments(session_id):
    """Erkennt Segmente aus Message-Timestamps und Inhalten.

    Returns: Liste von Segment-Dicts mit start/end Message-IDs
    """
    messages = get_session_messages(session_id)
    segments = []
    current_start = 0

    for i, msg in enumerate(messages):
        if msg['type'] != 'human':
            continue

        # Heuristik 1: Zeitliche Luecke
        if i > 0:
            prev_ts = messages[i-1].get('timestamp')
            curr_ts = msg.get('timestamp')
            if prev_ts and curr_ts:
                gap = (curr_ts - prev_ts).total_seconds() * 1000
                if gap > SEGMENT_GAP_MS:
                    segments.append(_create_segment(messages, current_start, i-1))
                    current_start = i
                    continue

        # Heuristik 2: Explizite Marker
        content = (msg.get('content') or '').lower()
        if any(kw in content for kw in TOPIC_CHANGE_KEYWORDS) and i > current_start + 2:
            segments.append(_create_segment(messages, current_start, i-1))
            current_start = i

    # Letztes Segment
    if current_start < len(messages):
        segments.append(_create_segment(messages, current_start, len(messages)-1))

    return segments


def _create_segment(messages, start_idx, end_idx):
    """Erzeugt ein Segment-Dict aus Message-Range."""
    segment_msgs = messages[start_idx:end_idx+1]
    return {
        'start_message_id': messages[start_idx]['id'],
        'end_message_id': messages[end_idx]['id'],
        'start_turn': _count_user_turns(messages, 0, start_idx),
        'end_turn': _count_user_turns(messages, 0, end_idx),
        'summary': _extract_summary(segment_msgs),
        'ai_has_writes': _has_writes(segment_msgs),
        'ai_tools_used': _extract_tools(segment_msgs),
        'files_touched': _extract_files(segment_msgs),
        'token_count': sum(m.get('tokens', 0) for m in segment_msgs),
        'duration_ms': _calc_duration(segment_msgs),
    }
```

### 15.4 Backend: Segment-API #spec-15-4-backend-segment-api

**GET `/api/sessions/<uuid>/segments`:**
- Liefert alle Segmente einer Session
- Automatische Erkennung beim ersten Aufruf (lazy)
- Response:
  ```json
  {
    "session_uuid": "abc-123",
    "segments": [
      {
        "index": 0,
        "start_turn": 1,
        "end_turn": 12,
        "summary": "Sprint 12 Governance implementiert",
        "outcome": "ok",
        "outcome_reason": null,
        "ai_has_writes": true,
        "files_touched": ["services/governance_service.py", "routes/governance_routes.py"],
        "token_count": 45000,
        "duration_ms": 1200000
      },
      {
        "index": 1,
        "start_turn": 13,
        "end_turn": 25,
        "summary": "Model Comparison Table Header Fix",
        "outcome": "needs_fix",
        "outcome_reason": "wrong_approach",
        "ai_has_writes": true,
        "files_touched": ["static/css/model-comparison.css"],
        "token_count": 12000,
        "duration_ms": 300000
      }
    ],
    "segment_count": 2,
    "auto_detected": true
  }
  ```

**POST `/api/sessions/<uuid>/segments/<index>/outcome`:**
- Body: `{outcome: "needs_fix", reason: "logic_error", severity: "high"}`
- Setzt Outcome fuer ein einzelnes Segment

**POST `/api/sessions/<uuid>/segments/split`:**
- Body: `{after_message_id: 123}`
- Manuelles Aufteilen: Fuegt Segmentgrenze nach Message ein
- Bestehende Segmente werden neu berechnet

**POST `/api/sessions/<uuid>/segments/merge`:**
- Body: `{segments: [0, 1]}`
- Zusammenfuehren zweier benachbarter Segmente

**POST `/api/sessions/<uuid>/segments/regenerate`:**
- Loescht alle Segmente und erkennt neu (Reset)

### 15.5 UI: Segment-Rating in Session-Detail #spec-15-5-ui-segment-rating-in-session-detail

**Segment-Leiste ueber dem Chat-Verlauf:**

```
┌─── Session: project_dashboard (Mar 31, 55 min) ──────────────────┐
│                                                                    │
│  Segments:                                                         │
│  ┌────────────────┐ ┌──────────────┐ ┌───────────────┐            │
│  │ #1 Governance   │ │ #2 Table Fix │ │ #3 Data Clean │            │
│  │ Turns 1-12      │ │ Turns 13-25  │ │ Turns 26-40   │            │
│  │ 45K tokens      │ │ 12K tokens   │ │ 8K tokens     │            │
│  │ [OK]            │ │ [Fix ▾]      │ │ [–]           │            │
│  └────────────────┘ └──────────────┘ └───────────────┘            │
│                                                                    │
│  [Split here] ← erscheint beim Hovern zwischen Messages           │
│                                                                    │
│  Chat-Verlauf...                                                   │
└────────────────────────────────────────────────────────────────────┘
```

**Interaktionen:**
- Klick auf Segment scrollt zum entsprechenden Abschnitt im Chat
- Klick auf `[OK]` / `[Fix]` / `[–]` oeffnet Quick-Rate Popup fuer dieses Segment
- "Split here" Button erscheint zwischen Messages beim Hovern
- Drag der Segment-Grenzen zum manuellen Verschieben (optional, v2)
- Segment-Farbe zeigt Outcome: gruen=OK, rot=Fix, grau=unrated

**Segment-Zusammenfassung:**
- Automatisch generierter 1-Zeiler aus erster User-Message
- Editierbar per Klick

### 15.6 Aggregation: Segment → Session Outcome #spec-15-6-aggregation-segment-session-outcome

**Automatisches Session-Outcome aus Segmenten:**

Wenn alle Segmente bewertet sind, wird das Session-Outcome automatisch abgeleitet:

| Segment-Outcomes | Session-Outcome |
|-----------------|----------------|
| Alle OK | OK |
| Mindestens 1 needs_fix, kein reverted | needs_fix |
| Mindestens 1 reverted | reverted |
| Mix aus OK und unvollstaendig | partial |

**Severity:** Hoechste Severity aller Segmente wird Session-Severity.

**Override:** User kann Session-Outcome manuell ueberschreiben (hat Vorrang).

### 15.7 Integration mit bestehenden Features #spec-15-7-integration-mit-bestehenden-features

**Rework-API (Sprint 9.3):**
- `reason_distribution` zaehlt jetzt Segment-Outcomes statt Session-Outcomes
- Genauere Daten: 1 schlechtes Segment in einer 5-Segment-Session = 20% statt 100%

**Rule-Generator (Sprint 12):**
- Kann Regeln auf Segment-Ebene generieren
- "In 8 von 10 Segmenten mit Write-Ops fehlten Tests" statt "8 Sessions hatten missing_tests"

**Model-Comparison (Sprint 11):**
- Quality-Score basiert auf Segment-Outcomes statt Session-Outcomes
- Genauerer Vergleich: Modell A hat 90% OK-Segmente vs. 70% OK-Sessions

**File-Heatmap (Sprint 10):**
- `files_touched` pro Segment ermoeglicht Zuordnung: Welche Datei in welchem Segment beruehrt
- Rework-Korrelation: "style.css wurde in 3 needs_fix Segmenten bearbeitet"

### 15.8 Backfill: Segmente fuer bestehende Sessions #spec-15-8-backfill-segmente-fuer-bestehende-sessions

**`scripts/backfill_segments.py` (neu):**

```bash
python3 scripts/backfill_segments.py                  # Alle Sessions
python3 scripts/backfill_segments.py --project X      # Nur ein Projekt
python3 scripts/backfill_segments.py --session UUID   # Nur eine Session
python3 scripts/backfill_segments.py --dry-run        # Nur anzeigen
```

Erkennt Segmente fuer alle bestehenden Sessions. Outcomes bleiben NULL
(muessen manuell bewertet werden). Nur die Segmentgrenzen werden gesetzt.

---

## Akzeptanzkriterien

- [ ] `session_segments` Tabelle mit Schema (15.2)
- [ ] Automatische Segment-Erkennung aus Timestamps + Inhalten (15.3)
- [ ] GET/POST API fuer Segmente: Liste, Outcome, Split, Merge, Regenerate (15.4)
- [ ] Segment-Leiste in Session-Detail mit Klick-to-Scroll (15.5)
- [ ] Quick-Rate pro Segment (OK/Fix/Rev + Reason + Severity) (15.5)
- [ ] "Split here" Button zwischen Messages (15.5)
- [ ] Session-Outcome wird aus Segmenten aggregiert (15.6)
- [ ] Rework-API nutzt Segment-Outcomes wenn vorhanden (15.7)
- [ ] Backfill-Script fuer bestehende Sessions (15.8)
- [ ] Bestehende Session-Level-Bewertung bleibt als Fallback (keine Breaking Changes)

---

## Nicht in diesem Sprint

- Drag-to-resize Segment-Grenzen (v2)
- AI-generierte Segment-Zusammenfassungen via LLM
- Automatische Outcome-Erkennung (AI bewertet sich selbst)
- Multi-User Segment-Review (Team-Feature)

---

## Technische Entscheidungen

| Aspekt | Entscheidung | Begruendung |
|--------|-------------|-------------|
| Erkennung | Heuristik (Zeitluecke + Keywords) | Kein LLM-Aufruf noetig, schnell, deterministisch |
| Speicherung | Eigene Tabelle `session_segments` | Saubere Trennung, keine Session-Schema-Aenderung |
| Lazy Detection | Segmente erst beim ersten Aufruf erzeugen | Kein Overhead beim Import |
| Aggregation | Automatisch + manueller Override | Best of both: Konsistenz + Flexibilitaet |
| Fallback | Session-Outcome bleibt wenn keine Segmente | Abwaertskompatibel, kein Zwang zum Segment-Rating |
