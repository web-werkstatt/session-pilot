function _showToast(msg, isError) {
    var toast = document.getElementById('syncToast');
    if (toast) {
        toast.textContent = msg;
        toast.className = 'toast show' + (isError ? ' toast-error' : '');
        setTimeout(function() { toast.className = 'toast'; }, 4000);
    }
}

function _escapeJsString(text) {
    return String(text || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function _slugifyPlanTitle(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'plan';
}

function _buildCopilotUrl(planId, planTitle) {
    var url = '/copilot?plan_id=' + encodeURIComponent(planId);
    var slug = _slugifyPlanTitle(planTitle);
    if (slug) url += '&plan=' + encodeURIComponent(slug);
    return url;
}

function _buildMarkerApiUrl(markerId) {
    var url = '/api/copilot/markers';
    if (markerId) url += '/' + encodeURIComponent(markerId);
    url += '?plan_id=' + encodeURIComponent(PLAN_ID);
    if (_currentMarkerPlanId && String(_currentMarkerPlanId) !== String(PLAN_ID)) {
        url = '/api/copilot/markers';
        if (markerId) url += '/' + encodeURIComponent(markerId);
        url += '?plan_id=' + encodeURIComponent(_currentMarkerPlanId);
    }
    if (_currentProjectId) url += '&project_id=' + encodeURIComponent(_currentProjectId);
    return url;
}

function _projectQueryParam() {
    return _currentProjectId ? '&project_id=' + encodeURIComponent(_currentProjectId) : '';
}

function _normalizeMarker(marker) {
    var normalized = Object.assign({}, marker || {});
    normalized.marker_id = String(normalized.marker_id || '');
    normalized.status = normalized.status || 'todo';
    normalized.titel = normalized.titel || 'Unbenannter Marker';
    normalized.plan_title = normalized.plan_title || ((_planInfo && _planInfo.title) ? _planInfo.title : '');
    normalized.ziel = normalized.ziel || '';
    normalized.naechster_schritt = normalized.naechster_schritt || '';
    normalized.prompt = normalized.prompt || '';
    normalized.prompt_suggestion = normalized.prompt_suggestion || '';
    normalized.risiko = normalized.risiko || '';
    normalized.checks = Array.isArray(normalized.checks) ? normalized.checks : [];
    normalized.last_session = normalized.last_session || '';
    normalized.updated_at = normalized.updated_at || '';
    normalized.execution_score = normalized.execution_score === null || normalized.execution_score === undefined || normalized.execution_score === '' ? null : Number(normalized.execution_score);
    normalized.execution_comment = normalized.execution_comment || '';
    normalized.last_execution_at = normalized.last_execution_at || '';
    normalized.sprint_tag = normalized.sprint_tag || '';
    normalized.spec_tag = normalized.spec_tag || '';
    normalized.is_activatable = normalized.is_activatable === true;
    normalized.gate_reason = normalized.gate_reason || '';
    return normalized;
}

function _renderChecksHtml(checks) {
    if (!checks || checks.length === 0) {
        return '<div class="panel-check-empty">Keine checks definiert</div>';
    }
    return checks.map(function(item) {
        return '<div class="panel-check-item"><i data-lucide="check" class="icon icon-xs"></i>' + escapeHtml(item) + '</div>';
    }).join('');
}

function _upsertSection(marker) {
    var idx = allSections.findIndex(function(item) { return item.marker_id === marker.marker_id; });
    if (idx >= 0) allSections[idx] = Object.assign({}, allSections[idx], marker);
    else allSections.push(marker);
}

function _markerThreadId(markerId) {
    return 'marker:' + PLAN_ID + ':' + markerId;
}

function _extractMarkerPlanId(plan) {
    var content = plan && plan.content ? String(plan.content) : '';
    var match = content.match(/plan-id:\s*([^\s*]+)/i);
    return match ? match[1].trim() : null;
}

function _deriveSprintPath() {
    if (_planInfo && _planInfo.filename) {
        return _planInfo.filename;
    }
    var markerPlanId = _currentMarkerPlanId || String(PLAN_ID);
    return markerPlanId;
}

/* === Plan Switcher === */
function _loadPlanSwitcher() {
    api.get('/api/copilot/stats')
        .then(function(data) {
            var plans = data.active_plans || [];
            var dd = document.getElementById('planSwitcherDD');
            var html = '';
            plans.forEach(function(p) {
                var cls = p.id === PLAN_ID ? ' active' : '';
                html += '<button class="copilot-plan-switch-item' + cls + '" onclick="switchPlan(' + p.id + ', \'' + _escapeJsString(p.title || ('Plan ' + p.id)) + '\')">'
                    + escapeHtml(p.title || 'Plan #' + p.id)
                    + '<small>' + escapeHtml(p.project_name || '') + ' &middot; ' + (p.status || '') + '</small>'
                    + '</button>';
            });
            if (plans.length > 0) {
                html += '<div class="copilot-plan-switch-divider"></div>';
            }
            html += '<button class="copilot-plan-switch-item" onclick="window.location.href=\'/plans\'">Show all plans &rarr;</button>';
            dd.innerHTML = html;
        })
        .catch(function() {});
}

function togglePlanSwitcher() {
    var dd = document.getElementById('planSwitcherDD');
    dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}

function switchPlan(planId, planTitle) {
    window.location.href = _buildCopilotUrl(planId, planTitle);
}

function _formatTokenCount(value) {
    var num = Number(value || 0);
    if (!isFinite(num)) return '0';
    return num.toLocaleString('de-DE');
}

function _formatUsd(value) {
    var num = Number(value || 0);
    if (!isFinite(num)) return '$0.00';
    if (num < 0.01) return '$' + num.toFixed(4);
    if (num < 1) return '$' + num.toFixed(2);
    return '$' + num.toFixed(2);
}
