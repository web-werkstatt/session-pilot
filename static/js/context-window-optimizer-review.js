(function() {
    // CWO Sprint Ticket 1.11: Review-Button + Bewertungs-Anzeige
    //
    // Zeigt Perplexity-Review-Ergebnisse im CWO-Panel:
    // - Review anfordern / Erneut reviewen Button
    // - Confidence-Badge + overall_safe Indikator
    // - Token-Assessment Vorher/Nachher
    // - Migration-Assessments (safe/unsafe farbcodiert, collapsible)
    // - Dedup-Feedback bei unveraenderter Analyse
    //
    // Abhaengigkeit: context-window-optimizer.js muss zuerst geladen sein
    // (stellt window.cwo.ratingTone bereit).

    var ASSESSMENT_STYLES = {
        safe:              {label: 'safe',         color: '#86efac', bg: 'rgba(34,197,94,0.12)'},
        unsafe:            {label: 'unsafe',       color: '#fca5a5', bg: 'rgba(239,68,68,0.12)'},
        needs_review:      {label: 'needs review', color: '#fcd34d', bg: 'rgba(251,191,36,0.12)'},
        insufficient_data: {label: 'no data',      color: 'rgba(148,163,184,0.82)', bg: 'rgba(148,163,184,0.08)'}
    };

    // ------------------------------------------------------------------
    // Review-Sektion (Wrapper mit data-Attribut fuer DOM-Updates)
    // ------------------------------------------------------------------

    function buildSection(reviewData) {
        return '<div data-cwo-review>' + buildContent(reviewData) + '</div>';
    }

    function buildContent(reviewData) {
        if (!reviewData) return '';

        if (reviewData.dedup_hit) {
            return '<div style="margin-top:8px;padding:8px 12px;background:rgba(125,211,252,0.08);border:1px solid rgba(125,211,252,0.18);border-radius:6px;font-size:12px;color:#7dd3fc">'
                + 'Review aktuell — keine Aenderung seit letztem Review</div>';
        }

        if (reviewData.error) {
            return '<div style="margin-top:8px;color:#fca5a5;font-size:12px">Review-Fehler: '
                + escapeHtml(reviewData.error) + '</div>';
        }

        var review = reviewData.perplexity_review;
        if (!review) return '';

        var ratingTone = window.cwo.ratingTone;
        var html = '';
        var conf = review.overall_confidence || 0;
        var confColor = conf >= 80 ? '#86efac' : conf >= 50 ? '#fcd34d' : '#fca5a5';
        var safeDot = review.overall_safe ? '#22c55e' : '#ef4444';
        var safeLabel = review.overall_safe ? 'Safe' : 'Unsafe';

        // Header: Confidence + Safe-Status
        html += '<div style="margin-top:10px;padding:8px 12px;background:rgba(192,132,252,0.06);border:1px solid rgba(192,132,252,0.18);border-radius:6px">'
            + '<div style="display:flex;align-items:center;gap:8px;font-size:12px">'
            + '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + safeDot + '"></span>'
            + '<span style="color:#e2e8f0;font-weight:600">Perplexity-Review</span>'
            + '<span style="color:' + confColor + ';font-size:11px">Confidence: ' + conf + '%</span>'
            + '<span style="color:' + (review.overall_safe ? '#86efac' : '#fca5a5') + ';font-size:11px;margin-left:auto">' + safeLabel + '</span>'
            + '</div>';

        if (review.summary) {
            html += '<div style="color:rgba(226,232,240,0.78);font-size:12px;margin-top:6px">' + escapeHtml(review.summary) + '</div>';
        }

        // Token-Assessment Vorher/Nachher
        var ta = review.token_assessment;
        if (ta) {
            var afterTone = ratingTone(ta.rating_after);
            html += '<div style="margin-top:8px;display:flex;align-items:center;gap:12px;font-size:11px">'
                + '<span style="color:rgba(148,163,184,0.82)">Tokens:</span>'
                + '<span style="color:#e2e8f0">' + formatTokens(ta.current_tokens || 0) + '</span>'
                + '<span style="color:rgba(148,163,184,0.5)">\u2192</span>'
                + '<span style="color:' + afterTone.color + '">' + formatTokens(ta.projected_tokens_after || 0) + '</span>'
                + '<span style="color:#86efac;font-weight:600">\u2212' + (ta.reduction_percent || 0) + '%</span>'
                + '</div>';
            if (ta.comment) {
                html += '<div style="color:rgba(148,163,184,0.64);font-size:11px;margin-top:2px;font-style:italic">' + escapeHtml(ta.comment) + '</div>';
            }
        }

        html += '</div>';

        // Migration-Assessments (collapsible)
        var assessments = review.migration_assessments || [];
        if (assessments.length) {
            var unsafeCount = 0, safeCount = 0, otherCount = 0;
            for (var i = 0; i < assessments.length; i++) {
                if (assessments[i].assessment === 'safe') safeCount++;
                else if (assessments[i].assessment === 'unsafe') unsafeCount++;
                else otherCount++;
            }
            var sumParts = [];
            if (safeCount) sumParts.push(safeCount + ' safe');
            if (unsafeCount) sumParts.push(unsafeCount + ' unsafe');
            if (otherCount) sumParts.push(otherCount + ' pruefen');

            var assessHtml = assessments.map(function(a) {
                var st = ASSESSMENT_STYLES[a.assessment] || ASSESSMENT_STYLES.insufficient_data;
                return '<div style="border-left:3px solid ' + st.color + ';padding:6px 10px;margin-bottom:4px;background:' + st.bg + ';border-radius:0 4px 4px 0;font-size:12px">'
                    + '<div style="display:flex;justify-content:space-between;align-items:center">'
                    + '<span style="color:#f8fafc;font-weight:600">' + escapeHtml(a.section_title || '') + '</span>'
                    + '<span style="color:' + st.color + ';font-size:11px">' + escapeHtml(a.assessment || '') + '</span>'
                    + '</div>'
                    + (a.reason ? '<div style="color:rgba(226,232,240,0.72);margin-top:2px">' + escapeHtml(a.reason) + '</div>' : '')
                    + '</div>';
            }).join('');

            html += '<details style="margin-top:6px">'
                + '<summary style="cursor:pointer;color:rgba(148,163,184,0.82);font-size:12px">'
                + assessments.length + ' Migration-Bewertung(en) — ' + sumParts.join(', ') + '</summary>'
                + '<div style="margin-top:6px">' + assessHtml + '</div>'
                + '</details>';
        }

        return html;
    }

    // ------------------------------------------------------------------
    // Review ausloesen (POST)
    // ------------------------------------------------------------------

    function trigger(panel, projectName) {
        var link = panel.querySelector('[data-action="cwo-review"]');
        if (link) {
            link.textContent = 'laeuft...';
            link.style.pointerEvents = 'none';
            link.style.color = 'rgba(148,163,184,0.72)';
        }

        api.post('/api/project/' + encodeURIComponent(projectName) + '/cwo/review', {})
            .then(function(data) {
                var result = data && data.result;
                var container = panel.querySelector('[data-cwo-review]');
                if (container) {
                    container.innerHTML = buildContent(result);
                }
                if (link) {
                    link.textContent = 'Erneut reviewen';
                    link.style.pointerEvents = '';
                    link.style.color = '#c084fc';
                }
            })
            .catch(function(e) {
                var container = panel.querySelector('[data-cwo-review]');
                if (container) {
                    container.innerHTML = '<div style="margin-top:8px;color:#fca5a5;font-size:12px">Review fehlgeschlagen: '
                        + escapeHtml(e && e.message || String(e)) + '</div>';
                }
                if (link) {
                    link.textContent = 'Review anfordern';
                    link.style.pointerEvents = '';
                    link.style.color = '#c084fc';
                }
            });
    }

    // ------------------------------------------------------------------
    // Review laden (GET)
    // ------------------------------------------------------------------

    function load(projectName) {
        return api.get('/api/project/' + encodeURIComponent(projectName) + '/cwo/review')
            .then(function(data) { return data && data.result; });
    }

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    window.cwoReview = {
        buildSection: buildSection,
        buildContent: buildContent,
        trigger: trigger,
        load: load
    };
})();
