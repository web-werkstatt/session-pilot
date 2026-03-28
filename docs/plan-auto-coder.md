# Plan: Automatische Code-Qualitaets-Pipeline im Dashboard

## Context

Automatisierte Quality-Pipeline die fuer alle Projekte unter `/mnt/projects/`:
1. Analyse-Reports erzeugt (`quality-report.json` pro Projekt)
2. Claude Code headless die Reports liest und Probleme behebt
3. Fortschritt im Dashboard pro Projekt anzeigt (Quality Score, Trend, offene Issues)

## Gesamtfluss

```
[Automatischer Scan]          [Claude Code Fix-Loop]         [Dashboard]
       │                              │                          │
  Alle Projekte scannen          Report lesen               Scores anzeigen
       │                              │                          │
  quality-report.json           Probleme beheben            Fortschritt/Trend
  in jedem Projekt                    │                          │
       │                         Neuer Scan                 Pro Projekt:
  DRYwall + Radon +             Report updaten              - Score (A-F)
  LOC + Dateigroessen                 │                     - Offene Issues
  + CSS/JS Analyse              Bis Level A                 - Verlauf
```

## Neue Dateien im Dashboard

```
auto_coder/
├── __init__.py
├── scanner.py           # Scannt Projekte, erzeugt quality-report.json
├── derep.py             # DeRep: 3-Ebenen Code-Bereinigung
├── fixer.py             # Claude Code headless Fix-Loop
├── config.py            # Schwellwerte, Scoring-Regeln

routes/
├── quality_routes.py    # API: /api/quality, /api/quality/<projekt>

templates/
├── (project_detail.html erweitern: neuer Tab "Code-Qualitaet")

static/
├── css/quality.css
├── js/quality.js
```

## Report-Format: quality-report.json

Wird in jedem Projekt unter `.quality/report.json` abgelegt:

```json
{
  "project": "project_dashboard",
  "scanned_at": "2026-03-28T14:30:00",
  "score": "B",
  "score_numeric": 72,
  "summary": {
    "total_files": 89,
    "total_loc": 23800,
    "languages": {"Python": 9700, "JavaScript": 8800, "CSS": 5300}
  },
  "issues": [
    {
      "id": "dup-001",
      "level": "warning",
      "category": "duplication",
      "title": "escapeHtml() in 6 JS-Dateien dupliziert",
      "files": ["static/js/documents.js", "static/js/news.js", ...],
      "fix_prompt": "Verschiebe escapeHtml() nach static/js/base.js und entferne die Kopien aus den 6 Dateien.",
      "status": "open",
      "fixed_at": null
    },
    {
      "id": "complexity-001",
      "level": "warning",
      "category": "complexity",
      "title": "scan_projects() CC=15 (Ziel: <=10)",
      "files": ["services/project_scanner.py"],
      "fix_prompt": "Refactore scan_projects() in kleinere Funktionen. Ziel: Cyclomatic Complexity <= 10.",
      "status": "open",
      "fixed_at": null
    },
    {
      "id": "size-001",
      "level": "info",
      "category": "file_size",
      "title": "document_routes.py hat 482 Zeilen (Limit: 500)",
      "files": ["routes/document_routes.py"],
      "fix_prompt": "Teile document_routes.py auf wenn es 500 Zeilen ueberschreitet.",
      "status": "open",
      "fixed_at": null
    }
  ],
  "history": [
    {"date": "2026-03-27", "score": 68, "open_issues": 14},
    {"date": "2026-03-28", "score": 72, "open_issues": 11}
  ]
}
```

## Scoring-System

| Score | Punkte | Bedeutung |
|-------|--------|-----------|
| A | 90-100 | Exzellent: Keine kritischen Issues |
| B | 75-89 | Gut: Wenige Warnings |
| C | 60-74 | Akzeptabel: Mehrere Issues |
| D | 40-59 | Problematisch: Viele Issues |
| F | 0-39 | Kritisch: Sofort handeln |

Punktabzuege:
- Duplikation (DRYwall): -5 pro Fund
- Hohe Komplexitaet (Radon CC > 10): -3 pro Funktion
- Datei ueber Groessenlimit: -2 pro Datei
- CSS ohne Design-Tokens (>50% inline): -2 pro Datei
- Undefinierte CSS-Variablen: -1 pro Vorkommen

## Module im Detail

### 1. `scanner.py` (~300 Zeilen)

```python
class ProjectQualityScanner:
    """Scannt ein Projekt und erzeugt quality-report.json"""

    def scan(self, project_path: str) -> QualityReport:
        """Orchestriert alle Checks."""
        issues = []
        issues += self._check_duplication(project_path)   # DRYwall/jscpd
        issues += self._check_complexity(project_path)     # Radon
        issues += self._check_file_sizes(project_path)     # Zeilen-Limits
        issues += self._check_css_tokens(project_path)     # CSS-Variablen
        issues += self._check_js_duplication(project_path) # JS-Funktionen

        score = self._calculate_score(issues)
        report = self._build_report(project_path, issues, score)
        self._save_report(project_path, report)
        return report

    def scan_all(self) -> list[QualityReport]:
        """Scannt alle Projekte unter /mnt/projects/"""

    # Check-Methoden:
    def _check_duplication(self, path) -> list[Issue]:
        """npx jscpd --reporters json --output .quality/"""

    def _check_complexity(self, path) -> list[Issue]:
        """radon cc -j (nur Python-Projekte)"""

    def _check_file_sizes(self, path) -> list[Issue]:
        """Prueft Limits: .py=500, .tsx=300, .css=400, .html=300"""

    def _check_css_tokens(self, path) -> list[Issue]:
        """rg fuer undefinierte/ungenutzte CSS-Variablen"""

    def _check_js_duplication(self, path) -> list[Issue]:
        """rg fuer gleiche Funktionsnamen in mehreren Dateien"""
```

### 2. `derep.py` (~200 Zeilen)

Wie im vorherigen Plan -- DeRep fuer Code-Bloecke + File-Writes.
Wird vom Fixer genutzt um Claude-Output zu bereinigen.

### 3. `fixer.py` (~150 Zeilen)

```python
class QualityFixer:
    """Liest quality-report.json, laesst Claude Code Issues beheben."""

    def fix_project(self, project_path: str, max_issues: int = 5):
        """
        1. Report laden
        2. Offene Issues nach Prioritaet sortieren
        3. Pro Issue: claude -p mit fix_prompt ausfuehren
        4. DeRep auf Output anwenden
        5. Issue-Status auf 'fixed' setzen
        6. Re-Scan nach allen Fixes
        """

    def _build_fix_prompt(self, issue: dict) -> str:
        """Baut Prompt aus Issue-Daten + Projekt-Kontext."""

    def _run_claude(self, prompt: str, project_path: str) -> dict:
        """claude -p --output-format json --model sonnet --permission-mode acceptEdits"""

    def _update_report(self, project_path, issue_id, status):
        """Setzt Issue-Status in quality-report.json."""
```

### 4. `quality_routes.py` (~120 Zeilen)

```python
# Blueprint: quality

GET  /api/quality                    # Alle Projekte: [{name, score, open_issues}]
GET  /api/quality/<name>             # Detail: voller Report
POST /api/quality/<name>/scan        # Scan triggern
POST /api/quality/<name>/fix         # Fix-Loop starten
GET  /api/quality/<name>/history     # Score-Verlauf
```

### 5. Dashboard-UI Erweiterung

**In `templates/index.html`**: Quality-Score Badge pro Projekt-Karte (A/B/C/D/F mit Farbe)

**In `templates/project_detail.html`**: Neuer Tab "Code-Qualitaet":
- Score-Anzeige (gross, farbig)
- Issue-Liste mit Status (open/fixed/ignored)
- Verlaufs-Chart (Chart.js, bereits via CDN geladen)
- Buttons: "Jetzt scannen", "Auto-Fix starten"

### 6. `config.py` (~40 Zeilen)

```python
QUALITY_DIR = ".quality"
REPORT_FILE = "report.json"

SCORE_WEIGHTS = {
    "duplication": -5,
    "complexity": -3,
    "file_size": -2,
    "css_tokens": -2,
    "css_undefined": -1,
}

FILE_SIZE_LIMITS = {
    ".py": 500, ".tsx": 300, ".jsx": 300,
    ".ts": 500, ".js": 500, ".css": 400,
    ".html": 300, ".astro": 300,
}

RADON_MIN_GRADE = "C"  # Alles >= C wird als Issue gemeldet
```

## Integration mit bestehendem Dashboard

### Projekt-Scanner erweitern
In `services/project_scanner.py` beim Scan: Quality-Score aus `.quality/report.json` laden und in Projektdaten einbetten → Dashboard zeigt Score sofort.

### Background-Job (optional)
In `services/notification_checker.py` (laeuft bereits als Thread alle 60s):
- Alle 24h: `scan_all()` fuer Quality-Reports
- Oder: als RemoteTrigger (wie Dashboard Health Check)

### Blueprint registrieren
In `routes/__init__.py`: `from routes.quality_routes import quality_bp`

## Implementierungs-Reihenfolge

1. `auto_coder/config.py` + `__init__.py` -- Package-Grundlage
2. `auto_coder/scanner.py` -- Kern: Scannt und erzeugt Reports
3. `auto_coder/derep.py` -- DeRep Algorithmus
4. `routes/quality_routes.py` -- API-Endpunkte
5. UI: Tab in project_detail.html + quality.css + quality.js
6. `auto_coder/fixer.py` -- Claude Code Fix-Loop
7. Dashboard-Integration: Score-Badge auf Projektkarten
8. Background-Job oder RemoteTrigger fuer automatische Scans

## Verifikation

```bash
# 1. Scanner testen
python -c "
from auto_coder.scanner import ProjectQualityScanner
s = ProjectQualityScanner()
report = s.scan('/mnt/projects/project_dashboard')
print(f'Score: {report[\"score\"]} ({report[\"score_numeric\"]})')
print(f'Issues: {len(report[\"issues\"])}')
"

# 2. Report pruefen
cat /mnt/projects/project_dashboard/.quality/report.json | python -m json.tool

# 3. API testen
curl http://localhost:5055/api/quality | python -m json.tool
curl http://localhost:5055/api/quality/project_dashboard | python -m json.tool

# 4. Fix-Loop testen
curl -X POST http://localhost:5055/api/quality/project_dashboard/fix

# 5. Dashboard pruefen: Score-Badge auf Projektkarten sichtbar
```

## Abgrenzung

- Kein eigenes LLM-Hosting (nutzt Claude via CLI)
- Kein RPG/DPO (nur DeRep Post-Processing)
- Fix-Loop optional -- kann auch nur Reports erzeugen ohne Auto-Fix
- Keine Test-Ausfuehrung (nur statische Analyse)
