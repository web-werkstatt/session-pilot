(function() {
    // CWO Sprint Ticket 1.8: Context Window Optimizer UI
    //
    // Read-Only Analyse-Anzeige im Tool-Files-Modal:
    // - Token-Budget-Badge am Topbar-Button (Page-Load)
    // - CWO-Panel im Modal: Findings, Migration-Map, File-Inventory
    // - "Analyse starten"-Link fuer On-Demand-Analyse

    var PANEL_ID = 'cwoPanelBanner';
    var BADGE_CLASS = 'tool-files-cwo-badge';

    // --------------------------------------------------------------------
    // Rating -> Farbe/Label
    // --------------------------------------------------------------------

    var RATING_TONES = {
        ok:      {label: 'OK',      color: '#86efac', dot: '#22c55e'},
        info:    {label: 'Info',     color: '#7dd3fc', dot: '#38bdf8'},
        warning: {label: 'Warning', color: '#fcd34d', dot: '#fbbf24'},
        error:   {label: 'Kritisch', color: '#fca5a5', dot: '#ef4444'}
    };
    var TONE_UNKNOWN = {label: 'unbekannt', color: 'rgba(148,163,184,0.82)', dot: '#94a3b8'};

    function ratingTone(rating) {
        return RATING_TONES[rating] || TONE_UNKNOWN;
    }

    var SEVERITY_COLORS = {
        error:   '#fca5a5',
        warning: '#fcd34d',
        info:    '#7dd3fc'
    };

    // --------------------------------------------------------------------
    // Badge auf Topbar-Button
    // --------------------------------------------------------------------

    function attachBadge(projectName) {
        var btn = document.querySelector('.topbar-btn[onclick*="openToolProfileAdapter"]');
        if (!btn) return;

        loadAnalysis(projectName).then(function(result) {
            renderBadge(btn, result);
        }).catch(function() {
            renderBadge(btn, null);
        });
    }

    function renderBadge(btn, result) {
        var rating = result && result.token_budget_rating;
        var tone = ratingTone(rating);
        var badge = btn.querySelector('.' + BADGE_CLASS);
        if (!badge) {
            badge = document.createElement('span');
            badge.className = BADGE_CLASS;
            badge.style.cssText = 'display:inline-block;width:8px;height:8px;border-radius:50%;margin-left:4px;vertical-align:middle;box-shadow:0 0 0 1px rgba(15,23,42,0.6)';
            btn.appendChild(badge);
        }
        badge.style.background = tone.dot;
        badge.title = 'CWO Token-Budget: ' + (result ? formatTokens(result.total_tokens) + ' Tokens — ' + tone.label : 'keine Analyse');
    }

    // --------------------------------------------------------------------
    // Panel im Modal
    // --------------------------------------------------------------------

    function mountPanel(projectName) {
        removePanel();
        var host = document.getElementById('toolProfileAdapterBody');
        if (!host) return;

        var panel = document.createElement('div');
        panel.id = PANEL_ID;
        panel.style.cssText = 'margin-bottom:16px';
        panel.innerHTML = '<div style="color:rgba(148,163,184,0.64);font-size:12px">Lade CWO-Analyse...</div>';
        host.parentNode.insertBefore(panel, host);

        loadAnalysis(projectName).then(function(result) {
            renderPanel(panel, result, projectName);
        }).catch(function() {
            renderPanel(panel, null, projectName);
        });
    }

    function removePanel() {
        var existing = document.getElementById(PANEL_ID);
        if (existing) existing.remove();
    }

    function renderPanel(panel, result, projectName) {
        var hasResult = result && !result.error && result.token_budget_rating;
        var tone = hasResult ? ratingTone(result.token_budget_rating) : TONE_UNKNOWN;

        // Status-Zeile
        var statusText;
        if (!result) {
            statusText = 'Keine CWO-Analyse vorhanden';
        } else if (result.error) {
            statusText = 'Analyse-Fehler: ' + escapeHtml(result.error);
        } else {
            var counts = result.finding_counts || {};
            var parts = [];
            if (counts.error) parts.push(counts.error + ' kritisch');
            if (counts.warning) parts.push(counts.warning + ' Warnung(en)');
            if (counts.info) parts.push(counts.info + ' Info');
            statusText = formatTokens(result.total_tokens) + ' Tokens'
                + (parts.length ? ' — ' + parts.join(', ') : ' — keine Findings');
        }

        // Analyse-Link
        var analyzeLabel = !hasResult ? 'Jetzt analysieren' : 'Erneut analysieren';
        var analyzeLink = ' · <a href="#" data-action="cwo-analyze" style="color:#7dd3fc;text-decoration:underline;font-size:12px">'
            + escapeHtml(analyzeLabel) + '</a>';

        // Age
        var ageSpan = '';
        if (result && result.updated_at) {
            var age = relativeAge(result.updated_at);
            if (age) {
                ageSpan = ' <span style="color:rgba(148,163,184,0.6);font-size:12px">· ' + escapeHtml(age) + '</span>';
            }
        }

        // Details
        var findingsHtml = buildFindingsSection(result);
        var migrationHtml = buildMigrationSection(result);
        var inventoryHtml = buildInventorySection(result);

        panel.innerHTML = ''
            + '<div style="background:rgba(15,23,42,0.52);border:1px solid rgba(148,163,184,0.18);border-radius:8px;padding:10px 14px">'
            + '<div style="display:flex;align-items:center;gap:10px">'
            + '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + tone.dot + ';flex-shrink:0"></span>'
            + '<div style="flex:1;font-size:13px;color:' + tone.color + '">'
            + escapeHtml(statusText) + ageSpan + analyzeLink
            + '</div>'
            + '</div>'
            + findingsHtml
            + migrationHtml
            + inventoryHtml
            + '</div>';

        var link = panel.querySelector('[data-action="cwo-analyze"]');
        if (link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                triggerAnalysis(panel, projectName);
            });
        }
    }

    // --------------------------------------------------------------------
    // Findings (Collapsible)
    // --------------------------------------------------------------------

    function buildFindingsSection(result) {
        if (!result || result.error) return '';
        var findings = result.findings || [];
        if (!findings.length) return '';

        var html = findings.map(function(f) {
            var color = SEVERITY_COLORS[f.severity] || '#7dd3fc';
            var tokensHint = f.estimated_tokens
                ? ' <span style="color:rgba(148,163,184,0.6)">(' + formatTokens(f.estimated_tokens) + ' Tokens)</span>'
                : '';
            var recommendation = f.recommendation
                ? '<div style="color:rgba(148,163,184,0.78);margin-top:2px;font-style:italic">' + escapeHtml(f.recommendation) + '</div>'
                : '';
            return ''
                + '<div style="border-left:2px solid ' + color + ';padding:6px 10px;margin-bottom:4px;background:rgba(2,6,23,0.38);border-radius:0 4px 4px 0;font-size:12px">'
                + '<div style="color:#f8fafc;font-weight:600">' + escapeHtml(f.title || '') + tokensHint + '</div>'
                + '<div style="color:rgba(226,232,240,0.72);margin-top:2px">' + escapeHtml(f.detail || '') + '</div>'
                + recommendation
                + '</div>';
        }).join('');

        return '<details style="margin-top:10px">'
            + '<summary style="cursor:pointer;color:rgba(148,163,184,0.82);font-size:12px">'
            + findings.length + ' Finding(s) anzeigen</summary>'
            + '<div style="margin-top:6px">' + html + '</div>'
            + '</details>';
    }

    // --------------------------------------------------------------------
    // Migration-Map (Collapsible)
    // --------------------------------------------------------------------

    function buildMigrationSection(result) {
        if (!result || result.error) return '';
        var map = result.migration_map || [];
        if (!map.length) return '';

        var html = '<table style="width:100%;font-size:11px;border-collapse:collapse">'
            + '<thead><tr style="color:rgba(148,163,184,0.82);text-align:left">'
            + '<th style="padding:4px 8px">Sektion</th>'
            + '<th style="padding:4px 8px">Ziel</th>'
            + '<th style="padding:4px 8px">Load-Mode</th>'
            + '<th style="padding:4px 8px;text-align:right">Tokens</th>'
            + '<th style="padding:4px 8px">Risiko</th>'
            + '</tr></thead><tbody>';

        html += map.map(function(m) {
            var riskColor = m.risk === 'none' ? '#86efac' : m.risk === 'low' ? '#fcd34d' : '#fca5a5';
            return '<tr style="border-top:1px solid rgba(148,163,184,0.1)">'
                + '<td style="padding:4px 8px;color:#e2e8f0">' + escapeHtml(m.section_title || '') + '</td>'
                + '<td style="padding:4px 8px;color:rgba(226,232,240,0.72)">' + escapeHtml(m.target || '') + '</td>'
                + '<td style="padding:4px 8px"><code style="font-size:10px;background:rgba(148,163,184,0.12);padding:1px 5px;border-radius:3px;color:#7dd3fc">' + escapeHtml(m.load_mode || '') + '</code></td>'
                + '<td style="padding:4px 8px;text-align:right;color:#e2e8f0">' + formatTokens(m.tokens_saved || 0) + '</td>'
                + '<td style="padding:4px 8px;color:' + riskColor + '">' + escapeHtml(m.risk || '-') + '</td>'
                + '</tr>';
        }).join('');

        html += '</tbody></table>';

        var totalSaved = map.reduce(function(s, m) { return s + (m.tokens_saved || 0); }, 0);

        return '<details style="margin-top:6px">'
            + '<summary style="cursor:pointer;color:rgba(148,163,184,0.82);font-size:12px">'
            + map.length + ' Migration(en) — ' + formatTokens(totalSaved) + ' Tokens einsparbar</summary>'
            + '<div style="margin-top:6px;overflow-x:auto">' + html + '</div>'
            + '</details>';
    }

    // --------------------------------------------------------------------
    // File-Inventory (Collapsible)
    // --------------------------------------------------------------------

    function buildInventorySection(result) {
        if (!result || result.error) return '';
        var files = result.file_inventory || [];
        if (!files.length) return '';

        var TYPE_LABELS = {
            tool_file_claude: 'CLAUDE.md',
            tool_file_codex: 'AGENTS.md',
            tool_file_gemini: 'GEMINI.md',
            next_session: 'next-session.md',
            subdir_claude_md: 'Unterverz.',
            global_rule: 'Global Rule'
        };

        var html = '<table style="width:100%;font-size:11px;border-collapse:collapse">'
            + '<thead><tr style="color:rgba(148,163,184,0.82);text-align:left">'
            + '<th style="padding:4px 8px">Datei</th>'
            + '<th style="padding:4px 8px">Typ</th>'
            + '<th style="padding:4px 8px;text-align:right">Zeilen</th>'
            + '<th style="padding:4px 8px;text-align:right">Tokens</th>'
            + '</tr></thead><tbody>';

        // Nach Tokens absteigend sortieren
        files.sort(function(a, b) { return (b.tokens || 0) - (a.tokens || 0); });

        html += files.map(function(f) {
            var shortPath = (f.file || '').replace(/^\/mnt\/projects\/[^/]+\//, '');
            var typeLabel = TYPE_LABELS[f.type] || f.type || '-';
            return '<tr style="border-top:1px solid rgba(148,163,184,0.1)">'
                + '<td style="padding:4px 8px;color:#e2e8f0;font-family:monospace;font-size:10px" title="' + escapeHtml(f.file || '') + '">' + escapeHtml(shortPath) + '</td>'
                + '<td style="padding:4px 8px;color:rgba(226,232,240,0.72)">' + escapeHtml(typeLabel) + '</td>'
                + '<td style="padding:4px 8px;text-align:right;color:#e2e8f0">' + (f.lines || 0) + '</td>'
                + '<td style="padding:4px 8px;text-align:right;color:#e2e8f0">' + formatTokens(f.tokens || 0) + '</td>'
                + '</tr>';
        }).join('');

        html += '</tbody></table>';

        var totalTokens = files.reduce(function(s, f) { return s + (f.tokens || 0); }, 0);

        return '<details style="margin-top:6px">'
            + '<summary style="cursor:pointer;color:rgba(148,163,184,0.82);font-size:12px">'
            + files.length + ' Datei(en) — ' + formatTokens(totalTokens) + ' Tokens gesamt</summary>'
            + '<div style="margin-top:6px;overflow-x:auto">' + html + '</div>'
            + '</details>';
    }

    // --------------------------------------------------------------------
    // Analyse ausloesen (Inline-Link)
    // --------------------------------------------------------------------

    function triggerAnalysis(panel, projectName) {
        var link = panel.querySelector('[data-action="cwo-analyze"]');
        if (link) {
            link.textContent = 'laeuft...';
            link.style.pointerEvents = 'none';
            link.style.color = 'rgba(148,163,184,0.72)';
        }

        api.post('/api/project/' + encodeURIComponent(projectName) + '/cwo/analyze', {force: true})
            .then(function(data) {
                var result = data && data.result;
                renderPanel(panel, result, projectName);
                // Badge synchron halten
                var btn = document.querySelector('.topbar-btn[onclick*="openToolProfileAdapter"]');
                if (btn) renderBadge(btn, result);
            })
            .catch(function(e) {
                panel.innerHTML = '<div style="color:#fca5a5;font-size:12px">Analyse fehlgeschlagen: '
                    + escapeHtml(e && e.message || String(e)) + '</div>';
            });
    }

    // --------------------------------------------------------------------
    // Helpers
    // --------------------------------------------------------------------

    function relativeAge(updatedAt) {
        if (!updatedAt) return null;
        try {
            var then = new Date(updatedAt).getTime();
            if (!isFinite(then)) return null;
            var diffH = Math.floor((Date.now() - then) / 3600000);
            if (diffH < 1) return 'gerade eben';
            if (diffH < 24) return 'vor ' + diffH + 'h';
            return 'vor ' + Math.floor(diffH / 24) + 'd';
        } catch (e) { return null; }
    }

    // --------------------------------------------------------------------
    // API
    // --------------------------------------------------------------------

    function loadAnalysis(projectName) {
        return api.get('/api/project/' + encodeURIComponent(projectName) + '/cwo/analyze')
            .then(function(data) { return data && data.result; });
    }

    // --------------------------------------------------------------------
    // Public API
    // --------------------------------------------------------------------

    window.cwo = {
        attachBadge: attachBadge,
        mountPanel: mountPanel
    };

    // --------------------------------------------------------------------
    // Auto-Mount Badge beim Page-Load
    // --------------------------------------------------------------------

    function autoMount() {
        if (typeof PROJECT_NAME !== 'undefined' && PROJECT_NAME) {
            attachBadge(PROJECT_NAME);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoMount);
    } else {
        autoMount();
    }
})();
