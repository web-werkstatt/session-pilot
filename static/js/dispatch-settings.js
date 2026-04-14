/**
 * Dispatch Settings — ADR-002 Stufe 2a Commit 8
 * Rendering + API fuer Settings-Panel (Perplexity-Modus, Tool-Toggles).
 * Ergaenzt Dispatch-Objekt um Settings-Methoden.
 *
 * Abhaengigkeiten: dispatch.js (Dispatch), api.js, base.js (escapeHtml)
 */
var DispatchSettings = (function() {
    'use strict';
    var _open = false;

    function render(settings, toolProfiles) {
        if (!_open) {
            return '<div class="dispatch-settings-toggle">'
                + '<button class="dispatch-btn dispatch-btn--ghost" onclick="Dispatch.toggleSettings()">'
                + '<i data-lucide="settings" class="icon icon-xs"></i> Dispatch Settings</button></div>';
        }

        var html = '<div class="dispatch-settings">';
        html += '<div class="dispatch-settings-header">';
        html += '<span class="dispatch-settings-title">Dispatch Settings</span>';
        html += '<button class="dispatch-btn dispatch-btn--ghost" onclick="Dispatch.toggleSettings()">Schliessen</button>';
        html += '</div>';

        // Perplexity-Modus
        var pmode = (settings && settings.perplexity_mode) || 'review_only';
        html += '<div class="dispatch-settings-row">';
        html += '<span class="dispatch-settings-label">Perplexity-Modus</span>';
        html += '<select class="dispatch-settings-select" onchange="Dispatch.updatePerplexityMode(this.value)">';
        ['off', 'review_only', 'suggest'].forEach(function(m) {
            var sel = m === pmode ? ' selected' : '';
            var label = m === 'off' ? 'Aus' : m === 'review_only' ? 'Nur Review' : 'Suggest + Review';
            html += '<option value="' + m + '"' + sel + '>' + label + '</option>';
        });
        html += '</select></div>';

        // Suggest-Button
        if (pmode === 'suggest') {
            html += '<div class="dispatch-settings-row">';
            html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.suggest()">Perplexity: Assignments vorschlagen</button>';
            html += '</div>';
        }

        // Tool-Dispatch-Toggles
        html += '<div class="dispatch-settings-subtitle">Dispatch pro Tool</div>';
        var activeProfiles = (toolProfiles || []).filter(function(p) { return p.active !== false; });
        if (activeProfiles.length === 0) {
            html += '<div class="dispatch-settings-empty">Keine aktiven Tool-Profile.</div>';
        } else {
            activeProfiles.forEach(function(p) {
                html += '<div class="dispatch-settings-tool-row">';
                html += '<span class="dispatch-settings-tool-name">' + escapeHtml(p.tool_id) + '</span>';
                html += '<label class="dispatch-toggle"><input type="checkbox"' + (p.dispatch_manual ? ' checked' : '')
                    + ' onchange="Dispatch.toggleToolDispatch(\'' + escapeHtml(p.tool_id) + '\', \'manual\', this.checked)"> Manual</label>';
                html += '<label class="dispatch-toggle"><input type="checkbox"' + (p.dispatch_pull ? ' checked' : '')
                    + ' onchange="Dispatch.toggleToolDispatch(\'' + escapeHtml(p.tool_id) + '\', \'pull\', this.checked)"> Pull</label>';
                html += '<span class="dispatch-settings-concurrent">max ' + (p.max_concurrent || 1) + '</span>';
                html += '</div>';
            });
        }

        html += '</div>';
        return html;
    }

    function toggle() {
        _open = !_open;
    }

    return { render: render, toggle: toggle };
})();

/* Methoden auf Dispatch haengen (nach dispatch.js geladen) */
(function() {
    'use strict';
    if (typeof Dispatch === 'undefined') return;

    Dispatch.toggleSettings = function() {
        DispatchSettings.toggle();
        Dispatch.refresh();
    };

    Dispatch.updatePerplexityMode = async function(mode) {
        try {
            await api.post('/api/dispatch/settings', { scope: 'global', perplexity_mode: mode });
            var s = Dispatch.getSettings() || {};
            s.perplexity_mode = mode;
            Dispatch.setSettings(s);
            Dispatch.refresh();
        } catch (e) { alert('Fehler: ' + (e.message || e)); }
    };

    Dispatch.toggleToolDispatch = async function(toolId, mode, enabled) {
        var body = {};
        body['dispatch_' + mode] = enabled;
        try {
            await api.post('/api/dispatch/settings/' + encodeURIComponent(toolId), body);
        } catch (e) { alert('Fehler: ' + (e.message || e)); }
    };

    Dispatch.suggest = async function() {
        try {
            var result = await api.post('/api/dispatch/suggest?project=' + encodeURIComponent(PROJECT_NAME));
            var count = (result && result.suggestions && result.suggestions.length) || 0;
            alert('Perplexity hat ' + count + ' Assignment(s) vorgeschlagen.');
            Dispatch.refresh();
        } catch (e) { alert('Suggest-Fehler: ' + (e.message || e)); }
    };
})();
