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
            _renderCockpitWfStepPill(workflow);
            _renderCockpitWfMarkers(workflow);
            _renderCockpitWfSignals(workflow);
            _renderCockpitWfHint(workflow);
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

var COCKPIT_WF_STEP_ICON = {
    gate_ready: 'key',
    active: 'play',
    execution: 'activity',
    write_back: 'file-text',
    rating: 'star'
};

function _cockpitWfActiveStep(workflow) {
    var steps = (workflow && workflow.steps) || [];
    var currentId = workflow && workflow.current_step;
    for (var i = 0; i < steps.length; i++) {
        if (steps[i].id === currentId) return steps[i];
    }
    return null;
}

/* Mapping: Workflow-Step-ID → Panel-Tab fuer CTA-Klick.
   Aktueller Step entscheidet, welcher Tab im Section-Panel oeffnet. */
var COCKPIT_WF_STEP_TAB = {
    gate_ready: 'output',
    active: 'chat',
    execution: 'chat',
    write_back: 'output',
    rating: 'history'
};

function _renderCockpitWfMarkers(workflow) {
    var container = document.getElementById('cockpitWfMarkers');
    if (!container) return;

    var current = workflow.current_marker || {};
    var next = workflow.next_marker || {};
    var activeStep = _cockpitWfActiveStep(workflow);
    var cta = activeStep && activeStep.cta_label ? activeStep.cta_label : '';
    var stepTab = activeStep && COCKPIT_WF_STEP_TAB[activeStep.id] ? COCKPIT_WF_STEP_TAB[activeStep.id] : 'chat';

    function _card(role, marker, roleLabel, extraClass, withCta) {
        var iconName = role === 'current' ? 'target' : 'arrow-right-circle';
        var planLine = marker.plan_id
            ? '<div class="cockpit-wf-card-plan">Plan ' + escapeHtml(String(marker.plan_id))
                + (marker.plan_title ? ': ' + escapeHtml(marker.plan_title) : '')
                + '</div>'
            : '';
        var ctaBtn = withCta && cta
            ? '<span class="cockpit-wf-card-cta"><i data-lucide="chevron-right" class="icon icon-xs"></i>' + escapeHtml(cta) + '</span>'
            : '';
        return '<button class="cockpit-wf-card ' + extraClass + '" type="button"'
            + ' onclick="openSectionPanel(\'' + _escapeJsString(marker.marker_id) + '\', \'' + _escapeJsString(stepTab) + '\')"'
            + ' title="' + escapeHtml(roleLabel) + '">'
            + '<span class="cockpit-wf-card-head">'
            +   '<i data-lucide="' + iconName + '" class="icon icon-sm cockpit-wf-card-icon"></i>'
            +   '<span class="cockpit-wf-card-role">' + escapeHtml(roleLabel) + '</span>'
            + '</span>'
            + '<span class="cockpit-wf-card-title">' + escapeHtml(marker.title || marker.marker_id) + '</span>'
            + planLine
            + ctaBtn
            + '</button>';
    }

    var html = '';
    if (current.marker_id) {
        html += _card('current', current, 'Current · aktueller Fokus', 'cockpit-wf-card--current', true);
    }
    if (next.marker_id) {
        html += _card('next', next, 'Next · naechster Marker', 'cockpit-wf-card--next', !current.marker_id);
    }
    if (!html) {
        html = '<div class="cockpit-wf-card cockpit-wf-card--empty"><span class="cockpit-wf-card-role">Keine aktiven Marker</span></div>';
    }

    container.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function _renderCockpitWfHint(workflow) {
    var el = document.getElementById('cockpitWfHint');
    if (!el) return;
    var step = _cockpitWfActiveStep(workflow);
    var hints = {
        gate_ready: 'Marker bereit — Prompt und Checks pruefen, dann starten.',
        active: 'Marker ist auf in_progress — Session starten, Thread beginnen.',
        execution: 'Eine Session arbeitet gerade dran — Thread oeffnen oder warten.',
        write_back: 'Marker abgeschlossen — Session-Ergebnis in die handoff.md uebertragen.',
        rating: 'Marker ist done, Bewertung fehlt — Score (0-5) und Kommentar vergeben.'
    };
    var msg = step && hints[step.id] ? hints[step.id] : '';
    el.textContent = msg;
    el.style.display = msg ? '' : 'none';
}

function _renderCockpitWfStepPill(workflow) {
    var el = document.getElementById('cockpitWfStepLabel');
    if (!el) return;
    var label = typeof workflowLoopCurrentStepLabel === 'function'
        ? workflowLoopCurrentStepLabel(workflow)
        : (workflow.current_step || 'Workflow');
    var iconName = COCKPIT_WF_STEP_ICON[workflow.current_step] || 'activity';
    el.innerHTML = '<i data-lucide="' + iconName + '" class="icon icon-xs"></i>'
        + '<span>' + escapeHtml(label) + '</span>';
    if (typeof lucide !== 'undefined') lucide.createIcons();
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
