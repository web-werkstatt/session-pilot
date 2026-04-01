/**
 * SPEC-AUDIT-INTEGRATION-V1-001: Audit Dashboard JS
 */

function _showError(msg) {
    const el = document.getElementById('auditError');
    el.textContent = msg;
    el.style.display = 'block';
}

function _hideError() {
    document.getElementById('auditError').style.display = 'none';
}

function _setLoading(on) {
    document.getElementById('auditLoading').style.display = on ? 'block' : 'none';
    document.getElementById('btnRunAudit').disabled = on;
    document.getElementById('btnLoadLatest').disabled = on;
}

function _statusClass(status) {
    const map = {
        'PASS': 'status-pass',
        'FAIL': 'status-fail',
        'PARTIAL': 'status-partial',
        'UNSICHER': 'status-unsicher',
        'ERFÜLLT': 'status-pass',
        'TEILWEISE ERFÜLLT': 'status-partial',
        'FEHLT': 'status-fail',
    };
    return map[status] || 'status-unsicher';
}

function _renderResult(data) {
    document.getElementById('auditResult').style.display = 'block';

    document.getElementById('resultSpecTitle').textContent = data.spec_title || data.spec_id;
    const badge = document.getElementById('resultOverallStatus');
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
    const sum = data.summary;
    if (sum) {
        const parts = Object.entries(sum.by_status || {})
            .filter(([, v]) => v > 0)
            .map(([k, v]) => '<span class="summary-chip ' + _statusClass(k) + '">' +
                escapeHtml(k) + ': ' + v + '</span>');
        document.getElementById('resultSummary').innerHTML =
            '<span class="summary-total">Gesamt: ' + sum.total + '</span> ' + parts.join(' ');
    }

    // Requirements
    const container = document.getElementById('resultRequirements');
    container.innerHTML = '';

    (data.results || []).forEach(function(r) {
        const row = document.createElement('div');
        row.className = 'req-row';

        let llmBadge = '';
        if (r.evidence && r.evidence.llm_review) {
            const opinion = r.evidence.llm_review.opinion || 'unknown';
            llmBadge = '<span class="llm-badge llm-' + escapeHtml(opinion) + '" title="LLM: ' +
                escapeHtml(r.evidence.llm_review.comment || '') + '">LLM: ' +
                escapeHtml(opinion) + '</span>';
        } else if (r.evidence && r.evidence.llm_review_error) {
            llmBadge = '<span class="llm-badge llm-error" title="' +
                escapeHtml(r.evidence.llm_review_error.message || '') + '">LLM: error</span>';
        }

        const evidenceHtml = _renderEvidence(r.evidence);

        row.innerHTML =
            '<div class="req-header" onclick="this.parentElement.classList.toggle(\'expanded\')">' +
                '<span class="req-key">' + escapeHtml(r.requirement_key) + '</span>' +
                '<span class="req-status ' + _statusClass(r.status) + '">' + escapeHtml(r.status) + '</span>' +
                llmBadge +
                '<span class="req-notes">' + escapeHtml(r.notes || '') + '</span>' +
                '<span class="req-expand-icon">&#9660;</span>' +
            '</div>' +
            '<div class="req-details">' + evidenceHtml + '</div>';

        container.appendChild(row);
    });
}

function _renderEvidence(evidence) {
    if (!evidence) return '<p class="no-evidence">Keine Evidence vorhanden</p>';

    let html = '';

    if (evidence.coverage != null) {
        html += '<div class="ev-item"><strong>Coverage:</strong> ' +
            Math.round(evidence.coverage * 100) + '%</div>';
    }
    if (evidence.matched_areas && evidence.matched_areas.length) {
        html += '<div class="ev-item"><strong>Matched:</strong> ' +
            evidence.matched_areas.map(escapeHtml).join(', ') + '</div>';
    }
    if (evidence.unmatched_areas && evidence.unmatched_areas.length) {
        html += '<div class="ev-item"><strong>Unmatched:</strong> ' +
            evidence.unmatched_areas.map(escapeHtml).join(', ') + '</div>';
    }
    if (evidence.llm_review) {
        const lr = evidence.llm_review;
        html += '<div class="ev-item ev-llm"><strong>LLM Review:</strong> ' +
            '<span class="llm-opinion llm-' + escapeHtml(lr.opinion || '') + '">' +
            escapeHtml(lr.opinion || 'unknown') + '</span> &mdash; ' +
            escapeHtml(lr.comment || '') +
            '<div class="ev-llm-meta">Model: ' + escapeHtml(lr.model || '?') +
            ' | ' + escapeHtml(lr.created_at || '') + '</div></div>';
    }
    if (evidence.llm_review_error) {
        const le = evidence.llm_review_error;
        html += '<div class="ev-item ev-error"><strong>LLM Error:</strong> ' +
            escapeHtml(le.code || '') + ' - ' + escapeHtml(le.message || '') + '</div>';
    }

    return html || '<p class="no-evidence">Leere Evidence</p>';
}

async function runAudit() {
    _hideError();
    const specId = document.getElementById('auditSpecId').value.trim();
    if (!specId) { _showError('Spec ID eingeben'); return; }

    let inputFacts;
    const raw = document.getElementById('auditInputFacts').value.trim();
    try {
        inputFacts = raw ? JSON.parse(raw) : {};
    } catch (e) {
        _showError('Input Facts ist kein gueltiges JSON: ' + e.message);
        return;
    }

    _setLoading(true);
    try {
        const data = await api.post('/api/audits/run', {
            spec_id: specId,
            input_facts: inputFacts,
        });
        _renderResult(data);
    } catch (err) {
        _showError(err.body?.error || err.message || 'Unbekannter Fehler');
        document.getElementById('auditResult').style.display = 'none';
    } finally {
        _setLoading(false);
    }
}

async function loadLatest() {
    _hideError();
    const specId = document.getElementById('auditSpecId').value.trim();
    if (!specId) { _showError('Spec ID eingeben'); return; }

    _setLoading(true);
    try {
        const data = await api.get('/api/audits/spec/' + encodeURIComponent(specId) + '/latest');
        _renderResult(data);
    } catch (err) {
        _showError(err.body?.error || err.message || 'Unbekannter Fehler');
        document.getElementById('auditResult').style.display = 'none';
    } finally {
        _setLoading(false);
    }
}

// Deep-Link Support: ?spec_id=X oder ?run_id=N
(function() {
    const params = new URLSearchParams(window.location.search);
    const runId = params.get('run_id');
    const specId = params.get('spec_id');

    if (runId) {
        _setLoading(true);
        api.get('/api/audits/' + encodeURIComponent(runId))
            .then(_renderResult)
            .catch(function(err) { _showError(err.body?.error || err.message); })
            .finally(function() { _setLoading(false); });
    } else if (specId) {
        document.getElementById('auditSpecId').value = specId;
        loadLatest();
    }
})();
