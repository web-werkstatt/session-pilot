(function() {
    // ADR-002 Stufe 1a: Setup-Reviewer UI-Modul
    // Ergaenzt das bestehende Tool-Files-Modal um eine Review-Section.

    var REVIEW_SECTION_ID = 'setupReviewerSection';
    var REVIEW_BODY_ID = 'setupReviewerBody';
    var REVIEW_MESSAGE_ID = 'setupReviewerMessage';
    var REVIEW_BUTTON_ID = 'setupReviewerRunBtn';

    function ensureReviewSection() {
        var existing = document.getElementById(REVIEW_SECTION_ID);
        if (existing) return existing;

        // Anker: das bestehende Tool-Profile-Modal hat ein toolProfileAdapterBody div.
        // Wir fuegen unsere Review-Section darunter ein.
        var host = document.getElementById('toolProfileAdapterBody');
        if (!host) return null;

        var section = document.createElement('div');
        section.id = REVIEW_SECTION_ID;
        section.style.cssText = 'border-top:1px solid rgba(148,163,184,0.22);margin-top:18px;padding-top:16px';
        section.innerHTML = ''
            + '<header style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px">'
            + '<div>'
            + '<div style="font-size:12px;text-transform:uppercase;letter-spacing:0.08em;color:rgba(148,163,184,0.82)">Setup-Reviewer</div>'
            + '<div style="color:#f8fafc;font-weight:600;font-size:15px">Perplexity prueft die AI-Tool-Einrichtung</div>'
            + '</div>'
            + '<button class="btn-save" type="button" id="' + REVIEW_BUTTON_ID + '">Review anfordern</button>'
            + '</header>'
            + '<div id="' + REVIEW_BODY_ID + '"></div>'
            + '<div id="' + REVIEW_MESSAGE_ID + '" style="margin-top:10px;font-size:13px;min-height:18px"></div>';
        host.parentNode.insertBefore(section, host.nextSibling);

        section.querySelector('#' + REVIEW_BUTTON_ID).addEventListener('click', triggerReview);
        return section;
    }

    function setReviewMessage(text, kind) {
        var el = document.getElementById(REVIEW_MESSAGE_ID);
        if (!el) return;
        el.textContent = text || '';
        el.style.color = kind === 'error' ? '#fca5a5' : kind === 'success' ? '#86efac' : 'rgba(226,232,240,0.72)';
    }

    function severityColor(severity) {
        if (severity === 'error') return '#fca5a5';
        if (severity === 'warn') return '#fcd34d';
        return '#7dd3fc';
    }

    function renderDriftWarning(drift) {
        if (!drift || !drift.has_drift) return '';
        var files = (drift.drifted_files || []).map(escapeHtml).join(', ');
        return ''
            + '<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.4);border-radius:8px;padding:10px 12px;margin-bottom:12px">'
            + '<div style="color:#fca5a5;font-weight:600;font-size:13px;margin-bottom:4px">Context-Drift erkannt</div>'
            + '<div style="color:rgba(226,232,240,0.82);font-size:12px;line-height:1.5">'
            + (files ? '<strong>Betroffen:</strong> ' + files + '<br>' : '')
            + escapeHtml(drift.reason || '')
            + '</div>'
            + '</div>';
    }

    function renderFinding(f) {
        var color = severityColor(f.severity);
        var autofix = f.can_autofix
            ? '<span style="color:#86efac;font-size:11px;margin-left:8px">auto-fixable</span>'
            : '';
        return ''
            + '<article style="border:1px solid rgba(148,163,184,0.18);border-left:3px solid ' + color + ';border-radius:8px;padding:10px 12px;background:rgba(15,23,42,0.52);margin-bottom:8px">'
            + '<header style="display:flex;justify-content:space-between;gap:12px;align-items:baseline">'
            + '<div style="color:#f8fafc;font-weight:600;font-size:14px">' + escapeHtml(f.title || '') + autofix + '</div>'
            + '<span style="color:' + color + ';font-size:11px;text-transform:uppercase">' + escapeHtml(f.severity || '') + ' · ' + escapeHtml(f.area || '') + '</span>'
            + '</header>'
            + '<div style="color:rgba(226,232,240,0.82);font-size:12px;margin-top:6px;line-height:1.5">' + escapeHtml(f.problem || '') + '</div>'
            + (f.why_it_matters ? '<div style="color:rgba(148,163,184,0.72);font-size:11px;margin-top:4px;font-style:italic">' + escapeHtml(f.why_it_matters) + '</div>' : '')
            + (f.recommended_change ? '<div style="color:#e2e8f0;font-size:12px;margin-top:6px;padding-top:6px;border-top:1px dashed rgba(148,163,184,0.2)"><strong>Empfehlung:</strong> ' + escapeHtml(f.recommended_change) + '</div>' : '')
            + '</article>';
    }

    function renderSuggestedBlocks(blocks) {
        if (!blocks || typeof blocks !== 'object') return '';
        var entries = Object.keys(blocks).filter(function(k) { return blocks[k] && blocks[k].trim(); });
        if (!entries.length) return '';
        return entries.map(function(filename) {
            return ''
                + '<details style="margin-top:8px;border:1px solid rgba(148,163,184,0.18);border-radius:8px;background:rgba(15,23,42,0.42)">'
                + '<summary style="cursor:pointer;padding:8px 12px;color:#f8fafc;font-size:13px;font-weight:600">Vorgeschlagener Block fuer ' + escapeHtml(filename) + '</summary>'
                + '<pre style="background:rgba(2,6,23,0.64);color:#e2e8f0;padding:10px 12px;border-radius:0 0 8px 8px;max-height:260px;overflow:auto;font-size:11px;line-height:1.45;margin:0">' + escapeHtml(blocks[filename]) + '</pre>'
                + '</details>';
        }).join('');
    }

    function renderResult(result) {
        var body = document.getElementById(REVIEW_BODY_ID);
        if (!body) return;

        if (!result) {
            body.innerHTML = '<div style="color:rgba(226,232,240,0.64);font-size:13px">Kein Review vorhanden. Klicke "Review anfordern".</div>';
            return;
        }

        if (result.error === 'query_failed') {
            body.innerHTML = '<div style="color:#fca5a5">Reviewer-Aufruf fehlgeschlagen: ' + escapeHtml(result.raw_response || '') + '</div>';
            return;
        }
        if (result.error === 'parse_failed') {
            body.innerHTML = '<div style="color:#fca5a5">Reviewer-Antwort nicht parsbar. Raw-Response gespeichert.</div>';
            return;
        }

        var drift = renderDriftWarning(result.context_drift);
        var summary = result.summary
            ? '<div style="color:rgba(226,232,240,0.9);font-size:13px;margin-bottom:10px;padding:8px 12px;background:rgba(15,23,42,0.42);border-radius:8px">' + escapeHtml(result.summary) + '</div>'
            : '';

        var findings = (result.findings || []).map(renderFinding).join('');
        if (!findings) findings = '<div style="color:rgba(148,163,184,0.72);font-size:12px">Keine Findings.</div>';

        var suggestedBlocks = renderSuggestedBlocks(result.suggested_blocks);

        var meta = ''
            + '<div style="color:rgba(148,163,184,0.64);font-size:11px;margin-top:10px">'
            + (result.reviewer_tool ? 'via ' + escapeHtml(result.reviewer_tool) : '')
            + (result.reviewer_model ? ' (' + escapeHtml(result.reviewer_model) + ')' : '')
            + (result.priority ? ' · Prioritaet: ' + escapeHtml(result.priority) : '')
            + '</div>';

        body.innerHTML = drift + summary + findings + suggestedBlocks + meta;
    }

    async function loadExistingReview(projectName) {
        try {
            var data = await api.get('/api/project/' + encodeURIComponent(projectName) + '/tool-setup/review');
            if (data && data.result) {
                renderResult(data.result);
                setReviewMessage('Letzter Review: ' + (data.result.updated_at || 'unbekannt'), 'info');
            } else {
                renderResult(null);
                setReviewMessage('', 'info');
            }
        } catch (e) {
            // Kein bestehendes Review ist kein Fehler
            renderResult(null);
        }
    }

    async function triggerReview() {
        if (typeof PROJECT_NAME === 'undefined' || !PROJECT_NAME) return;
        var btn = document.getElementById(REVIEW_BUTTON_ID);
        if (btn) btn.disabled = true;
        setReviewMessage('Review laeuft (Perplexity)...', 'info');

        try {
            var data = await api.post('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/tool-setup/review', {});
            if (data && data.result) {
                renderResult(data.result);
                if (data.result.error) {
                    setReviewMessage('Review abgeschlossen mit Fehler: ' + data.result.error, 'error');
                } else if (data.result.dedup_hit) {
                    setReviewMessage('Dedup: Kontext unveraendert, alter Review wiederverwendet.', 'info');
                } else {
                    setReviewMessage('Review gespeichert.', 'success');
                }
            }
        } catch (e) {
            setReviewMessage('Review fehlgeschlagen: ' + (e && e.message ? e.message : e), 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // Public API: wird von tool-profile-adapter.js beim Oeffnen des Modals aufgerufen
    window.setupReviewer = {
        mount: function(projectName) {
            ensureReviewSection();
            renderResult(null);
            setReviewMessage('', 'info');
            loadExistingReview(projectName);
        }
    };
})();
