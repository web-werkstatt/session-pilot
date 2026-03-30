# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-30
> **Status:** Usage Reports Seite live, Week-Daten aus Monitor entfernt
> **Naechste Aufgabe:** OTel verifizieren, Woechentlich/Monatlich-Views testen

---

## Naechste Session

### Prioritaet: Usage Reports verfeinern
- [ ] Woechentlich/Monatlich-Views in Usage Reports testen und validieren
- [ ] Custom Date Range testen
- [ ] Cache-Tokens (read/create) separat als Zeile oder Toggle in Tabelle

### OTel verifizieren
- [ ] `source ~/.bashrc` + neue Claude Session starten
- [ ] `/api/otel/metrics` pruefen ob Metriken ankommen
- [ ] OTel liefert KEINE Rate-Limit-% - nur cost/token/session Metriken
- [ ] P90-Limits bleiben Fallback bis Anthropic mehr via OTel exportiert

### Weitere Aufgaben
- [ ] Scoring-Tuning: Score-Cap pro Kategorie
- [ ] xpost Projekt auf DevBox aufsetzen

### Offene Punkte
- P90-Limits konservativer als Anthropic (~21% vs echte ~30% bei gleichem Verbrauch)
- Echte Anthropic-Limits nicht programmatisch zugaenglich (weder OTel noch JSONL)
- OTel Env-Vars muessen VOR Claude Code Start gesetzt sein
