/**
 * Cockpit Workflow Overview — kompakte Workflow-Darstellung im Cockpit.
 *
 * Laedt Daten via /api/cockpit/project/<name> und rendert:
 * - Mini-SVG-Ring (reuse von workflow-loop-svg.js)
 * - Current/Next-Marker als Pill-Badges
 * - Signal-Dots (Governance, Quality, Audit)
 * - Kollaps-Toggle
 */

var _cockpitWorkflowData = null;

function loadCockpitWorkflow() {
    if (!COCKPIT_PROJECT) return;

    api.get('/api/cockpit/project/' + encodeURIComponent(COCKPIT_PROJECT))
        .then(function(data) {
            _cockpitWorkflowData = data;
            var workflow = data.workflow || {};
            var overview = document.getElementById('cockpitWorkflowOverview');
            if (!overview) return;

            var hasSteps = Array.isArray(workflow.steps) && workflow.steps.length > 0;
            if (!hasSteps) return;

            overview.style.display = 'block';
            _renderCockpitWfRing(workflow);
            _renderCockpitWfStepLabel(workflow);
            _renderCockpitWfMarkers(workflow);
            _renderCockpitWfSignals(workflow);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function() {});
}

function _renderCockpitWfRing(workflow) {
    var container = document.getElementById('cockpitWfRing');
    if (!container || typeof renderWorkflowLoopSvg !== 'function') return;
    renderWorkflowLoopSvg(container, workflow, function(step) {
        _scrollToWorkflowStep(step);
    });
}

function _scrollToWorkflowStep(step) {
    if (!step) return;
    var overview = document.getElementById('cockpitWorkflowOverview');
    if (overview) overview.classList.remove('is-collapsed');
}

function _renderCockpitWfStepLabel(workflow) {
    var el = document.getElementById('cockpitWfStepLabel');
    if (!el) return;
    var label = typeof workflowLoopCurrentStepLabel === 'function'
        ? workflowLoopCurrentStepLabel(workflow)
        : (workflow.current_step || 'Workflow');
    el.textContent = label;
}

function _renderCockpitWfMarkers(workflow) {
    var container = document.getElementById('cockpitWfMarkers');
    if (!container) return;

    var current = workflow.current_marker || {};
    var next = workflow.next_marker || {};
    var html = '';

    if (current.marker_id) {
        html += '<span class="cockpit-wf-pill cockpit-wf-pill--current" '
            + 'onclick="openSectionPanel(\'' + _escapeJsString(current.marker_id) + '\')" '
            + 'title="Aktueller Marker">'
            + '<span class="cockpit-wf-pill-label">Current</span> '
            + escapeHtml(current.title || current.marker_id)
            + '</span>';
    }

    if (next.marker_id) {
        html += '<span class="cockpit-wf-pill cockpit-wf-pill--next" '
            + 'onclick="openSectionPanel(\'' + _escapeJsString(next.marker_id) + '\')" '
            + 'title="Naechster Marker">'
            + '<span class="cockpit-wf-pill-label">Next</span> '
            + escapeHtml(next.title || next.marker_id)
            + '</span>';
    }

    if (!html) {
        html = '<span class="cockpit-wf-pill cockpit-wf-pill--next">Keine aktiven Marker</span>';
    }

    container.innerHTML = html;
}

function _renderCockpitWfSignals(workflow) {
    var container = document.getElementById('cockpitWfSignals');
    if (!container) return;

    var signals = workflow.signals || {};
    var dots = [];

    var govColor = _signalColor(signals.governance_status);
    if (govColor) {
        dots.push('<span class="cockpit-wf-signal-dot" style="background:' + govColor + '" title="Governance: ' + escapeHtml(signals.governance_status || 'unknown') + '"></span>');
    }

    var qualColor = _qualityColor(signals.quality_score);
    if (qualColor) {
        dots.push('<span class="cockpit-wf-signal-dot" style="background:' + qualColor + '" title="Quality: ' + escapeHtml(String(signals.quality_score != null ? signals.quality_score : 'n/a')) + '"></span>');
    }

    var auditColor = _signalColor(signals.audit_status);
    if (auditColor) {
        dots.push('<span class="cockpit-wf-signal-dot" style="background:' + auditColor + '" title="Audit: ' + escapeHtml(signals.audit_status || 'unknown') + '"></span>');
    }

    container.innerHTML = dots.join('');
}

function _signalColor(status) {
    if (!status) return '#64748b';
    var map = {
        'green': '#22c55e', 'ok': '#22c55e', 'pass': '#22c55e', 'passed': '#22c55e',
        'yellow': '#f59e0b', 'warn': '#f59e0b', 'warning': '#f59e0b',
        'red': '#ef4444', 'fail': '#ef4444', 'failed': '#ef4444', 'blocked': '#ef4444',
        'none': '#64748b', 'unknown': '#64748b', 'n/a': '#64748b'
    };
    return map[String(status).toLowerCase()] || '#64748b';
}

function _qualityColor(score) {
    if (score == null) return '#64748b';
    var n = Number(score);
    if (isNaN(n)) return '#64748b';
    if (n >= 80) return '#22c55e';
    if (n >= 50) return '#f59e0b';
    return '#ef4444';
}

function toggleCockpitWorkflow() {
    var overview = document.getElementById('cockpitWorkflowOverview');
    if (!overview) return;
    overview.classList.toggle('is-collapsed');
}
