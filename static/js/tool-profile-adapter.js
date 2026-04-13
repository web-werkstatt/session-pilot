(function() {
    var MODAL_ID = 'toolProfileAdapterModal';

    function ensureModal() {
        var existing = document.getElementById(MODAL_ID);
        if (existing) return existing;

        var modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.id = MODAL_ID;
        modal.innerHTML = ''
            + '<div class="modal-content" style="max-width:860px">'
            + '<div class="modal-header">'
            + '<h2>Tool-Profile Regenerate</h2>'
            + '<button class="modal-close" type="button" onclick="closeModal(\'' + MODAL_ID + '\')">&times;</button>'
            + '</div>'
            + '<div class="modal-body">'
            + '<p style="color:rgba(226,232,240,0.78);margin:0 0 14px;font-size:14px;line-height:1.55">'
            + 'Pflegt den <code>DASHBOARD-GENERATED</code>-Block in <code>CLAUDE.md</code>, <code>AGENTS.md</code> und <code>GEMINI.md</code>. '
            + 'Manueller Text ausserhalb der Block-Marker bleibt unberuehrt.'
            + '</p>'
            + '<div id="toolProfileAdapterBody" style="display:grid;gap:14px"></div>'
            + '<div id="toolProfileAdapterMessage" style="margin-top:14px;font-size:13px;min-height:18px"></div>'
            + '<div class="modal-actions" style="margin-top:18px;display:flex;gap:10px;justify-content:flex-end">'
            + '<button class="btn-cancel" type="button" onclick="closeModal(\'' + MODAL_ID + '\')">Schliessen</button>'
            + '<button class="btn-save" type="button" id="toolProfileAdapterApplyBtn">Regenerate schreiben</button>'
            + '</div>'
            + '</div>'
            + '</div>';
        document.body.appendChild(modal);
        modal.querySelector('#toolProfileAdapterApplyBtn').addEventListener('click', applyRegenerate);
        return modal;
    }

    function renderResults(results) {
        var body = document.getElementById('toolProfileAdapterBody');
        if (!body) return;
        if (!results || !results.length) {
            body.innerHTML = '<div style="color:#fca5a5">Keine Ergebnisse erhalten.</div>';
            return;
        }

        body.innerHTML = results.map(function(r) {
            var modeLabel = r.mode === 'bootstrap' ? 'Erst-Setup'
                : r.mode === 'update' ? 'Update'
                : r.mode === 'noop' ? 'Keine Aenderungen' : (r.mode || 'unbekannt');
            var badgeColor = r.written ? '#86efac' : (r.mode === 'noop' ? '#7dd3fc' : '#fcd34d');
            var errorHtml = r.error ? '<div style="color:#fca5a5;margin-top:6px">' + escapeHtml(r.error) + '</div>' : '';
            var violationsHtml = (r.violations && r.violations.length)
                ? '<ul style="color:#fca5a5;margin:6px 0 0;padding-left:18px">' + r.violations.map(function(v) {
                    return '<li>' + escapeHtml(v) + '</li>';
                }).join('') + '</ul>'
                : '';
            var diffHtml = r.diff
                ? '<pre style="background:rgba(2,6,23,0.64);color:#e2e8f0;padding:10px 12px;border-radius:8px;max-height:320px;overflow:auto;font-size:12px;line-height:1.45;margin:8px 0 0">' + escapeHtml(r.diff) + '</pre>'
                : '<div style="color:rgba(226,232,240,0.64);font-size:12px;margin-top:6px">Kein Diff.</div>';

            return ''
                + '<section style="border:1px solid rgba(148,163,184,0.18);border-radius:10px;padding:12px 14px;background:rgba(15,23,42,0.52)">'
                + '<header style="display:flex;align-items:center;justify-content:space-between;gap:12px">'
                + '<div>'
                + '<div style="font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(148,163,184,0.82)">' + escapeHtml(r.tool || '?') + '</div>'
                + '<div style="color:#f8fafc;font-weight:600">' + escapeHtml(r.filename || '') + '</div>'
                + '</div>'
                + '<span style="color:' + badgeColor + ';font-size:12px;font-weight:700">' + escapeHtml(modeLabel) + '</span>'
                + '</header>'
                + diffHtml
                + violationsHtml
                + errorHtml
                + '</section>';
        }).join('');
    }

    function setMessage(text, kind) {
        var el = document.getElementById('toolProfileAdapterMessage');
        if (!el) return;
        el.textContent = text || '';
        el.style.color = kind === 'error' ? '#fca5a5' : kind === 'success' ? '#86efac' : 'rgba(226,232,240,0.72)';
    }

    async function openToolProfileAdapter() {
        if (typeof PROJECT_NAME === 'undefined' || !PROJECT_NAME) {
            alert('Projekt nicht gesetzt');
            return;
        }
        ensureModal();
        renderResults([]);
        setMessage('Preview wird geladen...', 'info');
        openModal(MODAL_ID);

        try {
            var data = await api.get('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/tool-profile/preview');
            renderResults(data.results || []);
            var changed = (data.results || []).filter(function(r) { return r.mode !== 'noop'; }).length;
            setMessage(changed ? (changed + ' Datei(en) wuerden aktualisiert.') : 'Alle Tool-Dateien sind aktuell.', 'info');
        } catch (e) {
            setMessage('Preview fehlgeschlagen: ' + (e && e.message ? e.message : e), 'error');
        }

        // ADR-002 Stufe 1a: Setup-Reviewer-Banner oben im Modal mounten
        // (kein zweiter Primaer-Button, nur Status + optionaler Inline-Link)
        if (window.setupReviewer && typeof window.setupReviewer.mountBanner === 'function') {
            window.setupReviewer.mountBanner(PROJECT_NAME);
        }

        // CWO Sprint Ticket 1.8: Context Window Optimizer Panel
        if (window.cwo && typeof window.cwo.mountPanel === 'function') {
            window.cwo.mountPanel(PROJECT_NAME);
        }
    }

    async function applyRegenerate() {
        var btn = document.getElementById('toolProfileAdapterApplyBtn');
        if (btn) btn.disabled = true;
        setMessage('Schreibe Tool-Dateien...', 'info');

        try {
            var data = await api.post('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/tool-profile/regenerate', {});
            renderResults(data.results || []);
            if (data.ok) {
                var written = (data.results || []).filter(function(r) { return r.written; }).length;
                setMessage(written ? (written + ' Datei(en) aktualisiert.') : 'Keine Aenderungen noetig.', 'success');
            } else {
                setMessage('Regenerate abgelehnt (Write-Guard Verletzung).', 'error');
            }
        } catch (e) {
            setMessage('Regenerate fehlgeschlagen: ' + (e && e.message ? e.message : e), 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    window.openToolProfileAdapter = openToolProfileAdapter;
})();
