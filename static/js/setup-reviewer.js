(function() {
    // ADR-002 Stufe 1a: Setup-Reviewer UI (Badge + Banner, kein eigener Button)
    //
    // Der Review ist Diagnose, nicht Aktion. Darum:
    // - Status-Badge am Tool-Files-Button (Page-Load)
    // - Banner oben im Modal (Modal-Open)
    // - Kein Primaer-CTA, nur ein kleiner Inline-Link "Jetzt aktualisieren"
    //   wenn der Review fehlt oder veraltet ist.

    var BANNER_ID = 'setupReviewerBanner';
    var BADGE_CLASS = 'tool-files-setup-badge';

    // ------------------------------------------------------------------------
    // Status-Ableitung
    // ------------------------------------------------------------------------

    function severityTone(result) {
        if (!result) {
            return {label: 'ungeprueft', color: 'rgba(148,163,184,0.82)', dot: '#94a3b8'};
        }
        if (result.error) {
            return {label: 'Reviewer-Fehler', color: '#fca5a5', dot: '#ef4444'};
        }
        var drift = result.context_drift && result.context_drift.has_drift;
        if (drift) {
            return {label: 'Context-Drift', color: '#fca5a5', dot: '#ef4444'};
        }
        var findings = result.findings || [];
        var errs = findings.filter(function(f) { return f.severity === 'error'; }).length;
        if (errs > 0) {
            return {label: errs + ' kritisch', color: '#fca5a5', dot: '#ef4444'};
        }
        var warns = findings.filter(function(f) { return f.severity === 'warn'; }).length;
        if (warns > 0) {
            return {label: warns + ' Finding(s)', color: '#fcd34d', dot: '#fbbf24'};
        }
        if (result.setup_ok === true) {
            return {label: 'OK', color: '#86efac', dot: '#22c55e'};
        }
        return {label: 'ungeprueft', color: 'rgba(148,163,184,0.82)', dot: '#94a3b8'};
    }

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

    function isStale(updatedAt) {
        if (!updatedAt) return true;
        try {
            var then = new Date(updatedAt).getTime();
            if (!isFinite(then)) return true;
            return (Date.now() - then) > 24 * 3600000;
        } catch (e) { return true; }
    }

    // ------------------------------------------------------------------------
    // Badge auf Topbar-Button
    // ------------------------------------------------------------------------

    function attachStatusBadge(projectName) {
        var btn = document.querySelector('.topbar-btn[onclick*="openToolProfileAdapter"]');
        if (!btn) return;

        loadReview(projectName).then(function(result) {
            renderBadge(btn, result);
        }).catch(function() {
            renderBadge(btn, null);
        });
    }

    function renderBadge(btn, result) {
        var tone = severityTone(result);
        var badge = btn.querySelector('.' + BADGE_CLASS);
        if (!badge) {
            badge = document.createElement('span');
            badge.className = BADGE_CLASS;
            badge.style.cssText = 'display:inline-block;width:8px;height:8px;border-radius:50%;margin-left:8px;vertical-align:middle;box-shadow:0 0 0 1px rgba(15,23,42,0.6)';
            btn.appendChild(badge);
        }
        badge.style.background = tone.dot;
        badge.title = 'Setup-Review: ' + tone.label;
    }

    // ------------------------------------------------------------------------
    // Banner im Modal
    // ------------------------------------------------------------------------

    function mountBanner(projectName) {
        removeBanner();
        var host = document.getElementById('toolProfileAdapterBody');
        if (!host) return;

        var banner = document.createElement('div');
        banner.id = BANNER_ID;
        banner.style.cssText = 'margin-bottom:16px';
        banner.innerHTML = '<div style="color:rgba(148,163,184,0.64);font-size:12px">Lade Review-Stand...</div>';
        host.parentNode.insertBefore(banner, host);

        loadReview(projectName).then(function(result) {
            renderBanner(banner, result, projectName);
        }).catch(function() {
            renderBanner(banner, null, projectName);
        });
    }

    function removeBanner() {
        var existing = document.getElementById(BANNER_ID);
        if (existing) existing.remove();
    }

    function renderBanner(banner, result, projectName) {
        var tone = severityTone(result);
        var age = result && result.updated_at ? relativeAge(result.updated_at) : null;
        var stale = !result || isStale(result && result.updated_at);

        var driftBar = '';
        if (result && result.context_drift && result.context_drift.has_drift) {
            var files = (result.context_drift.drifted_files || []).map(escapeHtml).join(', ');
            driftBar = ''
                + '<div style="background:rgba(239,68,68,0.14);border-left:3px solid #ef4444;padding:8px 12px;margin-bottom:10px;font-size:12px;color:#fecaca;border-radius:0 6px 6px 0">'
                + '<strong>Context-Drift:</strong> '
                + (files ? files : 'Tool-Dateien divergieren')
                + (result.context_drift.reason ? ' — <span style="color:rgba(254,202,202,0.72)">' + escapeHtml(result.context_drift.reason) + '</span>' : '')
                + '</div>';
        }

        var refreshLabel = !result ? 'Jetzt reviewen'
            : result.error ? 'Erneut versuchen'
            : stale ? 'Review aktualisieren'
            : 'Erneut reviewen';

        var refreshLink = refreshLabel
            ? ' · <a href="#" data-action="refresh-review" style="color:#7dd3fc;text-decoration:underline;font-size:12px">'
              + escapeHtml(refreshLabel) + '</a>'
            : '';

        var statusText;
        if (!result) {
            statusText = 'Kein Review vorhanden';
        } else if (result.error) {
            statusText = 'Reviewer-Fehler: ' + escapeHtml(result.error);
        } else {
            var count = (result.findings || []).length;
            statusText = count ? (count + ' Finding(s) · ' + tone.label) : ('Setup-Review: ' + tone.label);
        }

        var ageSpan = age
            ? ' <span style="color:rgba(148,163,184,0.6);font-size:12px">· ' + escapeHtml(age) + '</span>'
            : '';

        var summarySpan = '';
        if (result && result.summary && !result.error) {
            summarySpan = '<div style="color:rgba(226,232,240,0.72);font-size:12px;margin-top:4px;line-height:1.5">'
                + escapeHtml(result.summary) + '</div>';
        }

        var details = buildDetailsSection(result);

        banner.innerHTML = ''
            + driftBar
            + '<div style="background:rgba(15,23,42,0.52);border:1px solid rgba(148,163,184,0.18);border-radius:8px;padding:10px 14px">'
            + '<div style="display:flex;align-items:center;gap:10px">'
            + '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + tone.dot + ';flex-shrink:0"></span>'
            + '<div style="flex:1;font-size:13px;color:' + tone.color + '">'
            + statusText + ageSpan + refreshLink
            + '</div>'
            + '</div>'
            + summarySpan
            + details
            + '</div>';

        var link = banner.querySelector('[data-action="refresh-review"]');
        if (link) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                triggerReview(banner, projectName);
            });
        }
    }

    function buildDetailsSection(result) {
        if (!result || result.error) return '';
        var findings = result.findings || [];
        var blocks = result.suggested_blocks || {};
        var hasBlocks = Object.keys(blocks).some(function(k) { return blocks[k] && blocks[k].trim(); });
        if (!findings.length && !hasBlocks) return '';

        var findingsHtml = findings.length
            ? '<details style="margin-top:10px"><summary style="cursor:pointer;color:rgba(148,163,184,0.82);font-size:12px">' + findings.length + ' Finding(s) anzeigen</summary>'
              + '<div style="margin-top:6px">' + findings.map(renderFindingCompact).join('') + '</div></details>'
            : '';

        var blocksHtml = hasBlocks
            ? '<details style="margin-top:6px"><summary style="cursor:pointer;color:rgba(148,163,184,0.82);font-size:12px">Vorgeschlagene Bloecke anzeigen</summary>'
              + '<div style="margin-top:6px">' + renderSuggestedBlocks(blocks) + '</div></details>'
            : '';

        return findingsHtml + blocksHtml;
    }

    function renderFindingCompact(f) {
        var color = f.severity === 'error' ? '#fca5a5' : f.severity === 'warn' ? '#fcd34d' : '#7dd3fc';
        return ''
            + '<div style="border-left:2px solid ' + color + ';padding:6px 10px;margin-bottom:4px;background:rgba(2,6,23,0.38);border-radius:0 4px 4px 0;font-size:12px">'
            + '<div style="color:#f8fafc;font-weight:600">' + escapeHtml(f.title || '') + '</div>'
            + '<div style="color:rgba(226,232,240,0.72);margin-top:2px">' + escapeHtml(f.problem || '') + '</div>'
            + (f.recommended_change ? '<div style="color:rgba(148,163,184,0.78);margin-top:2px;font-style:italic">→ ' + escapeHtml(f.recommended_change) + '</div>' : '')
            + '</div>';
    }

    function renderSuggestedBlocks(blocks) {
        return Object.keys(blocks).filter(function(k) {
            return blocks[k] && blocks[k].trim();
        }).map(function(filename) {
            return ''
                + '<div style="margin-bottom:6px">'
                + '<div style="color:rgba(226,232,240,0.82);font-size:11px;font-weight:600;margin-bottom:2px">' + escapeHtml(filename) + '</div>'
                + '<pre style="background:rgba(2,6,23,0.64);color:#e2e8f0;padding:8px 10px;border-radius:6px;max-height:220px;overflow:auto;font-size:11px;line-height:1.45;margin:0">' + escapeHtml(blocks[filename]) + '</pre>'
                + '</div>';
        }).join('');
    }

    // ------------------------------------------------------------------------
    // Review ausloesen (via Inline-Link)
    // ------------------------------------------------------------------------

    function triggerReview(banner, projectName) {
        var link = banner.querySelector('[data-action="refresh-review"]');
        if (link) {
            link.textContent = 'laeuft...';
            link.style.pointerEvents = 'none';
            link.style.color = 'rgba(148,163,184,0.72)';
        }

        api.post('/api/project/' + encodeURIComponent(projectName) + '/tool-setup/review', {})
            .then(function(data) {
                renderBanner(banner, data && data.result, projectName);
                // Badge auf Topbar-Button synchron halten
                var btn = document.querySelector('.topbar-btn[onclick*="openToolProfileAdapter"]');
                if (btn) renderBadge(btn, data && data.result);
            })
            .catch(function(e) {
                banner.innerHTML = '<div style="color:#fca5a5;font-size:12px">Review fehlgeschlagen: ' + escapeHtml(e && e.message || String(e)) + '</div>';
            });
    }

    // ------------------------------------------------------------------------
    // API-Helper
    // ------------------------------------------------------------------------

    function loadReview(projectName) {
        return api.get('/api/project/' + encodeURIComponent(projectName) + '/tool-setup/review')
            .then(function(data) { return data && data.result; });
    }

    // ------------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------------

    window.setupReviewer = {
        attachStatusBadge: attachStatusBadge,
        mountBanner: mountBanner
    };

    // ------------------------------------------------------------------------
    // Auto-Mount des Badges beim Page-Load
    // ------------------------------------------------------------------------

    function autoMount() {
        if (typeof PROJECT_NAME !== 'undefined' && PROJECT_NAME) {
            attachStatusBadge(PROJECT_NAME);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoMount);
    } else {
        autoMount();
    }
})();
