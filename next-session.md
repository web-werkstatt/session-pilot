# Projekt-Dashboard - Naechste Session

> **Letzte Aktualisierung:** 2026-03-27
> **Status:** Sprint 1+2+3 abgeschlossen, Tech-Debt bereinigt
> **Naechste Aufgabe:** UI-Verbesserungen (CSS-Variablen, Lucide Icons)

---

## Naechste Session

### UI-Verbesserungen
- [ ] Verbleibende hardcoded Hex-Farben in CSS durch CSS-Variablen ersetzen
- [ ] Emoji-Icons in JS-generierten Inhalten durch Lucide ersetzen
- [ ] Plans: 3 nicht-zugeordnete Plans manuell zuordnen

### Infrastruktur
- [ ] Docker vs. systemd klaeren
- [ ] Tailwind CDN durch lokalen Build ersetzen (Production)

### Hinweise
- GitHub API: Private Repos brauchen gueltigen Token (einige PATs abgelaufen)
- Health-Checks: Viele Projekte mit Port zeigen "down" weil Service nicht laeuft - ggf. nur fuer aktive Container pruefen
- Security: pip-audit nicht installiert auf dem Server (`pip install pip-audit`)
