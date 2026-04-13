/**
 * Spec Audits Dashboard
 *
 * Laedt verfuegbare Specs, zeigt Run-Historie, vereinfachtes Formular.
 */
(function () {
    'use strict';

    // -----------------------------------------------------------------------
    // Init
    // -----------------------------------------------------------------------

    async function init() {
        await Promise.all([loadSpecs(), loadRecentRuns()]);
        handleDeepLink();
    }

    // -----------------------------------------------------------------------
    // Specs laden + Spec-Liste rendern
    // -----------------------------------------------------------------------

    var _specs = [];

    async function loadSpecs() {
        try {
            var data = await api.get('/api/audits/specs');
            _specs = data.specs || [];
            renderSpecList(_specs);
            populateDropdown(_specs);
        } catch (err) {
            document.getElementById('auditSpecList').innerHTML =
                '<div class="audit-empty">Keine Specs gefunden</div>';
        }
    }

    function renderSpecList(specs) {
        var el = document.getElementById('auditSpecList');
        if (!specs.length) {
            el.innerHTML = '<div class="audit-empty">Keine Specs vorhanden. Specs werden ueber die API oder Datenbank angelegt.</div>';
            return;
        }

        el.innerHTML = specs.map(function (s) {
            var runBadge = '';
            if (s.latest_run) {
                var cls = _statusClass(s.latest_run.overall_status);
                runBadge = '<span class="audit-status-badge audit-status-badge--sm ' + cls + '">' +
                    esc(s.latest_run.overall_status) + '</span>';
            } else {
                runBadge = '<span class="audit-status-badge audit-status-badge--sm status-none">Kein Run</span>';
            }

            return '<div class="spec-card" onclick="selectSpec(\'' + esc(s.spec_id) + '\')">' +
                '<div class="spec-card__top">' +
                    '<span class="spec-card__id">' + esc(s.spec_id) + '</span>' +
                    runBadge +
                '</div>' +
                '<div class="spec-card__title">' + esc(s.title) + '</div>' +
                (s.summary ? '<div class="spec-card__summary">' + esc(s.summary) + '</div>' : '') +
                '<div class="spec-card__meta">' +
                    '<span>' + s.requirement_count + ' Anforderungen</span>' +
                    (s.risk_level ? '<span>Risiko: ' + esc(s.risk_level) + '</span>' : '') +
                '</div>' +
            '</div>';
        }).join('');
    }

    function populateDropdown(specs) {
        var select = document.getElementById('auditSpecId');
        specs.forEach(function (s) {
            var opt = document.createElement('option');
            opt.value = s.spec_id;
            opt.textContent = s.spec_id + ' — ' + s.title;
            select.appendChild(opt);
        });
    }

    // Globale Funktion fuer onclick
    window.selectSpec = function (specId) {
        document.getElementById('auditSpecId').value = specId;
        // Zum Formular scrollen
        document.querySelector('.audit-run-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Visuelles Feedback
        document.getElementById('auditSpecId').classList.add('audit-select--highlight');
        setTimeout(function () {
            document.getElementById('auditSpecId').classList.remove('audit-select--highlight');
        }, 1500);
    };

    // -----------------------------------------------------------------------
    // Letzte Runs
    // -----------------------------------------------------------------------

    async function loadRecentRuns() {
        try {
            var data = await api.get('/api/audits/recent');
            renderRecentRuns(data.runs || []);
        } catch (err) {
            document.getElementById('auditRecentRuns').innerHTML =
                '<div class="audit-empty">Keine Runs gefunden</div>';
        }
    }

    function renderRecentRuns(runs) {
        var el = document.getElementById('auditRecentRuns');
        if (!runs.length) {
            el.innerHTML = '<div class="audit-empty">Noch keine Audits durchgefuehrt</div>';
            return;
        }

        var rows = runs.map(function (r) {
            var cls = _statusClass(r.overall_status);
            var duration = r.duration_ms != null ? r.duration_ms + ' ms' : '—';
            var time = r.started_at ? formatTimeAgo(r.started_at) : '—';
            return '<tr class="run-row" onclick="loadRunById(' + r.run_id + ')">' +
                '<td><span class="audit-status-badge audit-status-badge--sm ' + cls + '">' +
                    esc(r.overall_status || '?') + '</span></td>' +
                '<td class="run-spec">' + esc(r.spec_title) + '</td>' +
                '<td class="run-id">#' + r.run_id + '</td>' +
                '<td class="run-time">' + esc(time) + '</td>' +
                '<td class="run-duration">' + esc(duration) + '</td>' +
            '</tr>';
        }).join('');

        el.innerHTML = '<table class="audit-table">' +
            '<thead><tr>' +
                '<th>Status</th><th>Spec</th><th>Run</th><th>Wann</th><th>Dauer</th>' +
            '</tr></thead>' +
            '<tbody>' + rows + '</tbody></table>';
    }

    window.loadRunById = function (runId) {
        _setLoading(true);
        api.get('/api/audits/' + runId)
            .then(_renderResult)
            .catch(function (err) { _showError(err.body?.error || err.message); })
            .finally(function () { _setLoading(false); });
    };

    // -----------------------------------------------------------------------
    // Audit starten / Latest laden
    // -----------------------------------------------------------------------

    window.runAudit = async function () {
        _hideError();
        var specId = document.getElementById('auditSpecId').value;
        if (!specId) { _showError('Bitte eine Spec auswaehlen'); return; }

        var filesText = document.getElementById('auditChangedFiles').value.trim();
        var changedFiles = filesText
            ? filesText.split('\n').map(function (l) { return l.trim(); }).filter(Boolean)
            : [];

        _setLoading(true);
        try {
            var data = await api.post('/api/audits/run', {
                spec_id: specId,
                input_facts: { changed_files: changedFiles },
            });
            _renderResult(data);
            loadRecentRuns(); // Run-Historie aktualisieren
        } catch (err) {
            _showError(err.body?.error || err.message || 'Unbekannter Fehler');
            document.getElementById('auditResult').style.display = 'none';
        } finally {
            _setLoading(false);
        }
    };

    window.loadLatest = async function () {
        _hideError();
        var specId = document.getElementById('auditSpecId').value;
        if (!specId) { _showError('Bitte eine Spec auswaehlen'); return; }

        _setLoading(true);
        try {
            var data = await api.get('/api/audits/spec/' + encodeURIComponent(specId) + '/latest');
            _renderResult(data);
        } catch (err) {
            _showError(err.body?.error || err.message || 'Unbekannter Fehler');
            document.getElementById('auditResult').style.display = 'none';
        } finally {
            _setLoading(false);
        }
    };

    // -----------------------------------------------------------------------
    // Result rendern
    // -----------------------------------------------------------------------

    function _renderResult(data) {
        var el = document.getElementById('auditResult');
        el.style.display = 'block';
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });

        document.getElementById('resultSpecTitle').textContent = data.spec_title || data.spec_id;
        var badge = document.getElementById('resultOverallStatus');
        badge.textContent = data.overall_status;
        badge.className = 'audit-status-badge ' + _statusClass(data.overall_status);

        document.getElementById('resultSpecId').textContent = 'Spec: ' + data.spec_id;
        document.getElementById('resultDuration').textContent = data.duration_ms != null
            ? 'Dauer: ' + data.duration_ms + ' ms' : '';
        document.getElementById('resultStarted').textContent = data.started_at
            ? 'Start: ' + formatDateTime(data.started_at) : '';
        document.getElementById('resultRunId').textContent = data.run_id
            ? 'Run #' + data.run_id : '';

        // Summary
        var sum = data.summary;
        if (sum) {
            var parts = Object.entries(sum.by_status || {})
                .filter(function (e) { return e[1] > 0; })
                .map(function (e) {
                    return '<span class="summary-chip ' + _statusClass(e[0]) + '">' +
                        esc(e[0]) + ': ' + e[1] + '</span>';
                });
            document.getElementById('resultSummary').innerHTML =
                '<span class="summary-total">Gesamt: ' + sum.total + '</span> ' + parts.join(' ');
        }

        // Requirements
        var container = document.getElementById('resultRequirements');
        container.innerHTML = '';

        (data.results || []).forEach(function (r) {
            var row = document.createElement('div');
            row.className = 'req-row';

            var llmBadge = '';
            if (r.evidence && r.evidence.llm_review) {
                var opinion = r.evidence.llm_review.opinion || 'unknown';
                llmBadge = '<span class="llm-badge llm-' + esc(opinion) + '" title="LLM: ' +
                    esc(r.evidence.llm_review.comment || '') + '">LLM: ' + esc(opinion) + '</span>';
            } else if (r.evidence && r.evidence.llm_review_error) {
                llmBadge = '<span class="llm-badge llm-error" title="' +
                    esc(r.evidence.llm_review_error.message || '') + '">LLM: error</span>';
            }

            var evidenceHtml = _renderEvidence(r.evidence);

            row.innerHTML =
                '<div class="req-header" onclick="this.parentElement.classList.toggle(\'expanded\')">' +
                    '<span class="req-key">' + esc(r.requirement_key) + '</span>' +
                    '<span class="req-status ' + _statusClass(r.status) + '">' + esc(r.status) + '</span>' +
                    llmBadge +
                    '<span class="req-notes">' + esc(r.notes || '') + '</span>' +
                    '<span class="req-expand-icon">&#9660;</span>' +
                '</div>' +
                '<div class="req-details">' + evidenceHtml + '</div>';

            container.appendChild(row);
        });
    }

    function _renderEvidence(evidence) {
        if (!evidence) return '<p class="no-evidence">Keine Evidence vorhanden</p>';

        var html = '';

        if (evidence.coverage != null) {
            html += '<div class="ev-item"><strong>Coverage:</strong> ' +
                Math.round(evidence.coverage * 100) + '%</div>';
        }
        if (evidence.matched_areas && evidence.matched_areas.length) {
            html += '<div class="ev-item"><strong>Matched:</strong> ' +
                evidence.matched_areas.map(esc).join(', ') + '</div>';
        }
        if (evidence.unmatched_areas && evidence.unmatched_areas.length) {
            html += '<div class="ev-item"><strong>Unmatched:</strong> ' +
                evidence.unmatched_areas.map(esc).join(', ') + '</div>';
        }
        if (evidence.llm_review) {
            var lr = evidence.llm_review;
            html += '<div class="ev-item ev-llm"><strong>LLM Review:</strong> ' +
                '<span class="llm-opinion llm-' + esc(lr.opinion || '') + '">' +
                esc(lr.opinion || 'unknown') + '</span> &mdash; ' +
                esc(lr.comment || '') +
                '<div class="ev-llm-meta">Model: ' + esc(lr.model || '?') +
                ' | ' + esc(lr.created_at || '') + '</div></div>';
        }
        if (evidence.llm_review_error) {
            var le = evidence.llm_review_error;
            html += '<div class="ev-item ev-error"><strong>LLM Error:</strong> ' +
                esc(le.code || '') + ' - ' + esc(le.message || '') + '</div>';
        }

        return html || '<p class="no-evidence">Leere Evidence</p>';
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    function _statusClass(status) {
        var map = {
            'PASS': 'status-pass', 'FAIL': 'status-fail',
            'PARTIAL': 'status-partial', 'UNSICHER': 'status-unsicher',
            'ERFÜLLT': 'status-pass', 'TEILWEISE ERFÜLLT': 'status-partial',
            'FEHLT': 'status-fail',
        };
        return map[status] || 'status-unsicher';
    }

    function _showError(msg) {
        var el = document.getElementById('auditError');
        el.textContent = msg;
        el.style.display = 'block';
    }

    function _hideError() {
        document.getElementById('auditError').style.display = 'none';
    }

    function _setLoading(on) {
        document.getElementById('auditLoading').style.display = on ? 'flex' : 'none';
        document.getElementById('btnRunAudit').disabled = on;
        document.getElementById('btnLoadLatest').disabled = on;
    }

    function esc(s) {
        return typeof escapeHtml === 'function' ? escapeHtml(s) : String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function handleDeepLink() {
        var params = new URLSearchParams(window.location.search);
        var runId = params.get('run_id');
        var specId = params.get('spec_id');

        if (runId) {
            _setLoading(true);
            api.get('/api/audits/' + encodeURIComponent(runId))
                .then(_renderResult)
                .catch(function (err) { _showError(err.body?.error || err.message); })
                .finally(function () { _setLoading(false); });
        } else if (specId) {
            document.getElementById('auditSpecId').value = specId;
            window.loadLatest();
        }
    }

    // -----------------------------------------------------------------------
    // Start
    // -----------------------------------------------------------------------

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
