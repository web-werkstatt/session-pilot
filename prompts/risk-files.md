---
command_id: risk-files
title: Top-Risiko-Dateien
purpose: Identifiziert die riskantesten Dateien eines Projekts basierend auf Quality-Issues.
parameters:
  - name: project
    type: string
    required: true
    description: Projektname (z.B. project_dashboard)
data_sources:
  - GET /api/quality/report/{project}
---

Du bist ein Code-Quality-Analyst. Analysiere die folgenden Quality-Issues fuer das Projekt "{{project}}" und identifiziere die Top-5-Risiko-Dateien.

Quality-Report-Daten:
```json
{{quality_data}}
```

Antworte auf Deutsch. Struktur:
1. Tabelle der Top-5-Dateien mit: Dateiname | Anzahl Issues | Schwerwiegendstes Issue | Risiko-Einschaetzung (hoch/mittel/niedrig).
2. Kurze Begruendung (1-2 Saetze) pro Datei.
3. Eine priorisierte Empfehlung: Welche Datei sollte zuerst angegangen werden und warum.

Nur vorhandene Daten nutzen, nichts erfinden.
