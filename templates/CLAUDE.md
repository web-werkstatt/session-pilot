# Templates — Architektur-Kontext

## Basis-Template

`base.html` laedt alle globalen Assets (api.js, base.js, base.css) und definiert Sidebar-Navigation.

## Konventionen

- Jinja2 mit `{% extends "base.html" %}` und `{% block content %}`
- Partials mit Underscore-Prefix: `_project_documents_tab.html`
- Seiten-spezifisches JS/CSS am Ende des Templates laden
- Modal-Overlays nutzen das generische Modal-System aus base.js (siehe `static/CLAUDE.md`)

## Groesse

Templates unterliegen dem 300-Zeilen-Limit. Bei Ueberschreitung: Tabs oder Sektionen als Partials extrahieren.
