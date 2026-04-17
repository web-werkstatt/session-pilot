# Sprint N — Copilot UX Redesign: "AI-native Work OS" #sprint-sprint-n-copilot-ux-redesign-ai-native-work-os

**Stand:** 2026-04-02
**Ziel:** Copilot Board von "Kanban + Chat" zu "AI-native Work OS" transformieren
**Status:** IN PROGRESS

---

## Vision

> **"AI Execution Pipeline"** — nicht "Board mit Chat"

Das Copilot Board soll sich anfühlen wie Linear/GitHub PRs — ein lebendiges, produktives Work OS, nicht ein statisches Kanban.

---

## UX-Probleme (vorher)

| Problem | Beschreibung |
|---------|--------------|
| Board visuell "tot" | Zu viel leerer Space, Cards wirken verloren |
| Chat versteckt | Chat nur im Modal — verschenktes Potenzial |
| Keine klare Story | User weiß nicht, was Section/Tasks sind |
| Modal falsch | Modal = isoliert, Workflow = kontinuierlich |
| Keine Guidance | Kein Microcopy, kein Flow-Hint |

---

## Lösungen (nachher)

### 1. Split View — Chat sichtbar machen #spec-1-split-view-chat-sichtbar-machen

```
┌─────────────────────┬──────────────────────┐
│                     │                      │
│   Board (links)     │   Panel (rechts)     │
│   Sections als      │   Aktive Section     │
│   Karten            │   + Live Chat        │
│                     │                      │
│   [Card klicken] ───┼───▶ Chat öffnet      │
│                     │                      │
└─────────────────────┴──────────────────────┘
```

**Implementation:**
- Layout: CSS Grid mit `grid-template-columns: 1fr 400px`
- Panel rechts einschieben bei Card-Klick
- Panel mit Transition: `transform: translateX(100%)` → `translateX(0)`
- Panel zeigt: Section-Header, AI-Preview, Chat-Verlauf, Input

### 2. Rich Cards mit AI-Preview #spec-2-rich-cards-mit-ai-preview

**Neue Card-Struktur:**
```
┌────────────────────────────────────┐
│ [Spec]  Title der Section          │
├────────────────────────────────────┤
│ 💡 Spec | 🧠 3 msgs | ⏱ 2h ago    │
├────────────────────────────────────┤
│ "Letzte AI-Antwort: Ich würde..." │
└────────────────────────────────────┘
```

**Felder:**
- Typ-Badge (Spec/Section)
- AI-Message-Count aus copilot_messages
- Letzte Aktivität (timestamp)
- **Preview der letzten AI-Antwort** (erste Zeile, 80 chars)

### 3. Side Panel statt Modal #spec-3-side-panel-statt-modal

**Warum:**
- Modal = isoliert, underbricht Flow
- Panel = kontinuierlich, kann offen bleiben
- Linear/GitHub PRs Pattern

**Panel-Struktur:**
```
┌────────────────────────────────────┐
│ ← Board    Section Title    [×]    │
├────────────────────────────────────┤
│ [Status Badge]  Spec-Ref: SPEC-X   │
├────────────────────────────────────┤
│ Letzte AI-Antwort:                 │
│ ┌────────────────────────────────┐ │
│ │ "Ich würde die Governance      │ │
│ │ direkt in den Tab integrieren" │ │
│ └────────────────────────────────┘ │
├────────────────────────────────────┤
│                                    │
│  Chat Verlauf                      │
│  ┌────────────────────────────┐   │
│  │ Du: Wie soll ich vorgehen? │   │
│  └────────────────────────────┘   │
│  ┌────────────────────────────┐   │
│  │ Copilot: Erst die Spec... │   │
│  └────────────────────────────┘   │
│                                    │
├────────────────────────────────────┤
│ [📎] [  Nachricht eingeben...  ]   │
└────────────────────────────────────┘
```

### 4. Spalten mit Semantik + Microcopy #spec-4-spalten-mit-semantik-microcopy

**Vorher:**
```
| Backlog | Ready | In Progress | ...
```

**Nachher:**
```
┌─────────────┐
│ 💡 BACKLOG  │
│ Ideen die   │
│ noch unklar │
│ sind        │
│             │
│ 3 Items     │
└─────────────┘

┌─────────────┐
│ 🚀 READY    │
│ Bereit für  │
│ Copilot     │
│             │
│ 2 Items     │
└─────────────┘

┌─────────────┐
│ ⚡ IN PROG  │
│ Wird mit    │
│ Copilot     │
│ bearbeitet  │
│             │
│ 1 Item      │
└─────────────┘
```

**Alle Spalten:**
| Spalte | Emoji | Semantik | Microcopy |
|--------|-------|----------|-----------|
| backlog | 💡 | Ideen | "Noch zu klären" |
| ready | 🚀 | Bereit | "Bereit für Copilot" |
| in_progress | ⚡ | Active | "Wird bearbeitet" |
| review | 👀 | Prüfen | "Zur Kontrolle" |
| done | ✅ | Fertig | "Abgeschlossen" |
| blocked | 🚧 | Blockiert | "Wartet auf..." |

### 5. Flow Guidance #spec-5-flow-guidance

**Oben im Board:**
```
┌────────────────────────────────────────────────────────┐
│ 1️⃣ Section erstellen → 2️⃣ Copilot ausführen → 3️⃣ Review │
└────────────────────────────────────────────────────────┘
```

### 6. Section → "AI Step" #spec-6-section-ai-step

**Rename:**
- UI: "Step" oder "AI Step" als Label
- Intern: `kind` bleibt `section`/`spec`

**Tooltips:**
- "AI Step": Ein Arbeitsschritt mit Copilot-Support
- "Spec": Detaillierte Spezifikation

### 7. Landing Page — "Continue where you left off" #spec-7-landing-page-continue-where-you-left-off

**Neue Struktur:**
```
┌────────────────────────────────────────────────────────┐
│ 🧠 Copilot                                       [?] │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Weiterarbeiten:                                       │
│  ┌──────────────────────────────────────────────────┐ │
│  │ 🚀 Governance-Features / Spec implementieren     │ │
│  │    Letzte AI-Antwort: "Ich würde zuerst..."    │ │
│  │                              [Weiterarbeiten →] │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  Schnellstart:                                        │
│  [+ Neue Section starten]  [+ Plan-Template wählen]   │
│                                                        │
│  ──────────────────────────────────────────────────── │
│                                                        │
│  Aktive Plans:                                        │
│  [Plan 1]  [Plan 2]  [Plan 3]                        │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 8. Visuelle Energie erhöhen #spec-8-visuelle-energie-erh-hen

**Cards:**
- Hover: subtle glow (`box-shadow: 0 0 20px rgba(59,130,246,0.3)`)
- Background: leicht heller als Column
- Border: subtil, wird bei Hover prominent

**Columns:**
- Background-Tint je nach Status
- Header mit Emoji prominent

**Farben:**
- AI/Copilot: Purple (#8b5cf6)
- Ready: Blue (#3b82f6)
- In Progress: Orange (#f59e0b)
- Review: Cyan (#06b6d4)
- Done: Green (#10b981)
- Blocked: Red (#ef4444)

---

## Datei-Änderungen

| Datei | Änderung |
|-------|----------|
| `copilot_board.html` | Split View Layout, Side Panel |
| `copilot_board.js` | Panel-Toggle, Rich Cards, AI-Preview |
| `copilot.css` | Panel-Styles, Glow-Effects, Microcopy |
| `copilot_landing.html` | "Continue where you left off" |
| `copilot_landing.js` | Letzte Aktivität laden |
| `copilot_landing.css` | Quick-Start Section |
| `plan_section_service.py` | `get_section_with_ai_preview()` |

---

## API-Erweiterungen

### GET /api/copilot/last-activity #spec-get-api-copilot-last-activity
```json
{
  "last_section": {
    "id": 123,
    "plan_id": 145,
    "plan_title": "Governance Features",
    "section_title": "Spec implementieren",
    "last_message_preview": "Ich würde zuerst die Spec...",
    "message_count": 5,
    "last_activity": "2026-04-02T12:30:00Z"
  }
}
```

---

## Implementation-Reihenfolge

1. [x] Split View Layout in copilot_board.html
2. [x] Side Panel mit Chat-Integration
3. [x] Rich Cards mit AI-Preview
4. [x] Spalten-Microcopy
5. [x] Flow Guidance Header
6. [x] Landing Page Redesign
7. [x] Visuelle Energie (Glows, Hover-Effects)

---

## Success Criteria

- [x] Split View funktioniert (Board links, Panel rechts)
- [x] Cards zeigen AI-Preview der letzten Antwort
- [x] Side Panel öffnet/schließt mit Animation
- [x] Spalten haben Microcopy und Semantik
- [x] Landing Page zeigt "Continue where you left off"
- [x] Visuell "lebendig" — nicht mehr "tot"

---

## Sprint-Commit

Commit: `TBD` nach Abschluss (Server-Restart erforderlich)
