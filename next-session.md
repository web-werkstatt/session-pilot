# Projekt-Dashboard - Session-Zusammenfassung

## Letztes Update: 2026-01-18

## Implementierte Features (diese Session)

### 1. Manuelle Projekt-Beziehungen
- **Globale Seite** `/dependencies` mit Liste und interaktivem Graph
- **Beziehungstypen**: hängt ab von, ersetzt, erweitert, nutzt, verwandt mit, Fork von, eigenständiges Modul, Teil von
- **Graph-Features**:
  - Drag & Drop von Projekten aus Liste
  - Shift+Klick zum Verbinden
  - Rechtsklick zum Einfärben von Knoten
  - Doppelklick auf Linie zum Löschen
  - Positionen und Farben werden in localStorage gespeichert
  - Graph scrollbar (auch nach unten)

### 2. Hybrid-Beziehungen im Edit-Modal
- Tab-Navigation: "Allgemein" | "Beziehungen"
- Ausgehende/eingehende Beziehungen pro Projekt
- Neue Beziehung direkt im Modal erstellen
- Ajax-Suche für Projekt-Auswahl

### 3. Beziehungs-Badges in Dashboard-Liste
- Kleine farbige Icons nach dem Projektnamen
- Tooltip zeigt Beziehungsdetails
- Ausgehend = volle Badges, Eingehend = gestrichelt

### 4. Ideen/Notizen-System
- Modal über 💡 Icon im Header
- Kategorien: Feature, Verbesserung, Bug, Notiz, Research, Frage
- Prioritäten und Projekt-Zuordnung
- Filter nach Kategorie und Status

### 5. Projekt-Assets-Endpunkt
- Bilder aus Projekten werden serviert (auch aus Sub-Projekten)
- Unterstützte Formate: png, jpg, jpeg, gif, svg, webp, ico
- CSS für verkleinerte Darstellung (max 300px Höhe)

## Dateistruktur

```
/mnt/projects/project_dashboard/
├── app.py                    # Flask-Backend mit allen API-Endpunkten
├── config.py                 # Konfiguration (PROJECTS_DIR, HOST, PORT)
├── relations.json            # Beziehungen und Beziehungstypen
├── ideas.json                # Ideen/Notizen
├── groups.json               # Benutzerdefinierte Gruppen
├── templates/
│   ├── index.html            # Haupt-Dashboard
│   ├── dependencies.html     # Beziehungen-Seite mit Graph
│   ├── containers.html       # Container-Übersicht
│   ├── vorlagen.html         # Vorlagen-Sammlung
│   └── news.html             # News-Seite
└── static/
    └── favicon.svg
```

## API-Endpunkte

### Beziehungen
- `GET /api/relations` - Alle Beziehungen
- `POST /api/relations` - Neue Beziehung erstellen
- `DELETE /api/relations/<id>` - Beziehung löschen
- `GET /api/relations/types` - Beziehungstypen
- `GET /api/project/<name>/relations` - Beziehungen für ein Projekt

### Ideen
- `GET /api/ideas` - Alle Ideen
- `POST /api/ideas` - Neue Idee
- `PUT /api/ideas/<id>` - Idee aktualisieren
- `DELETE /api/ideas/<id>` - Idee löschen

### Projekte
- `GET /api/projects/search?q=<query>` - Ajax-Suche

### Assets
- `GET /<pfad>` - Bilder aus Projekten (z.B. `/archon-ui-main/public/img.png`)

## Mögliche nächste Schritte

- [ ] Graph: Zoom-Funktion
- [ ] Graph: Export als Bild
- [ ] Beziehungen: Import/Export als JSON
- [ ] Ideen: Tags/Labels
- [ ] Ideen: Deadline/Erinnerung
- [ ] Dashboard: Projekt-Suche verbessern
- [ ] Dashboard: Favoriten-System

## Server starten

```bash
cd /mnt/projects/project_dashboard
python3 app.py
# Läuft auf http://0.0.0.0:5055
```

## Git Status

- Branch: `main`
- Remote: `origin` (git.webideas24.com)
- Letzter Commit: `3fc8385` - Graph-Verbesserungen und Projekt-Assets-Endpunkt
