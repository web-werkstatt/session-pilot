# Static Assets — Architektur-Kontext

## Fetch-Wrapper `api.js`

Zentraler HTTP-Client, eingebunden in base.html vor base.js. KEIN rohes `fetch()` in Seiten-JS verwenden.

- `api.get(url)`, `api.post(url, body)`, `api.put()`, `api.del()`
- `api.request(url, opts)` — fuer Downloads: `{raw: true}`
- Wirft `api.ApiError` bei Fehlern
- Automatisches JSON-Parsing, Content-Type, Status-Check

## Globale JS-Utilities `base.js`

Auf allen Seiten verfuegbar — NICHT in einzelnen JS-Dateien duplizieren:
- `formatTokens()`, `formatDate()`, `formatDateTime()`, `escapeHtml()`, `formatTimeAgo()`
- Neue Utility-Funktionen die in >1 Seite gebraucht werden gehoeren hierher

## Generisches Modal-System `base.js`

- `openModal(id)`, `closeModal(id)`, Modal-Stack (`_modalStack`)
- Globaler Escape-Handler und delegierter Overlay-Click
- KEINE eigenen Escape-Handler oder `classList.add/remove('show')` in Seiten-JS
- Fuer Modals mit Cleanup: benannte Wrapper (z.B. `closeEditModal()`) die `closeModal(id)` aufrufen

## Workflow-Loop Assets

Aufgeteilt auf `window.WorkflowLoop`-Namespace:
- `js/workflow-loop/state.js`, `cards.js`, `board.js`, `modal.js`, `actions.js`
- `js/workflow-loop.js` — Orchestrator
- `css/workflow-loop-shell.css`, `-cards.css`, `-forms.css`, `-summary.css`

## Dashboard-Widgets

Chart.js via CDN, Lazy-Loading beim Tab-Wechsel.
