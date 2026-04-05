var _lastActivity = null;

document.addEventListener('DOMContentLoaded', function() {
    loadCopilotStats();
    if (typeof lucide !== 'undefined') lucide.createIcons();
});

function loadCopilotStats() {
    api.get('/api/copilot/stats')
        .then(function(data) {
            document.getElementById('statPlans').textContent = data.plans_total || 0;
            document.getElementById('statActive').textContent = data.plans_active || 0;
            document.getElementById('statSections').textContent = data.sections_total || 0;
            renderRecentProjects(data.recent_projects || []);
            renderActivePlans(data.active_plans || []);
            renderContinueState(data.active_plans || []);
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function() {
            document.getElementById('statPlans').textContent = '?';
            document.getElementById('statActive').textContent = '?';
            document.getElementById('statSections').textContent = '?';
        });
}

function renderRecentProjects(projects) {
    var container = document.getElementById('recentProjectsList');
    if (!projects.length) {
        container.innerHTML = '<span style="font-size:12px;color:var(--text-secondary);opacity:0.5;">Keine Projekte</span>';
        return;
    }

    container.innerHTML = projects.map(function(p) {
        return '<a href="/plans?project=' + encodeURIComponent(p.project_name) + '" class="recent-project-item">'
            + '<span class="rp-name">' + escapeHtml(p.project_name) + '</span>'
            + '<span class="rp-pills"><span class="stat-pill stat-pill-total">' + p.plan_count + '</span></span>'
            + '</a>';
    }).join('');
}

function renderActivePlans(plans) {
    var container = document.getElementById('activePlansList');
    var empty = document.getElementById('emptyState');

    if (!plans.length) {
        container.innerHTML = '';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    container.innerHTML = plans.map(function(plan) {
        return '<a href="' + buildCopilotUrl(plan.id, plan.title, plan.project_name || '') + '" class="plan-card-link">'
            + '<div class="plan-card" style="border-left:3px solid #818cf8;">'
            + '<div style="display:flex;align-items:center;gap:8px;padding:10px 12px;">'
            + '<span style="font-size:12px;font-weight:600;flex:1;">' + escapeHtml(plan.title) + '</span>'
            + '<span class="badge badge-cat"><i data-lucide="zap" class="icon icon-xs"></i> Starten</span>'
            + '</div>'
            + '<div style="padding:0 12px 10px;font-size:11px;color:var(--text-secondary);">' + (plan.project_name || 'Kein Projekt') + '</div>'
            + '</div></a>';
    }).join('');
}

function renderContinueState(plans) {
    var section = document.getElementById('continueSection');
    if (!section) return;
    _lastActivity = plans.length ? plans[0] : null;
    if (!_lastActivity) {
        section.style.display = 'none';
        return;
    }

    document.getElementById('continuePlanName').textContent = _lastActivity.project_name || 'Kein Projekt';
    document.getElementById('continueSectionTitle').textContent = _lastActivity.title || ('Plan ' + _lastActivity.id);
    document.getElementById('continuePreview').textContent = 'Zuletzt aktiver Einstieg im Cockpit fuer dieses Projekt.';
    section.style.display = '';
}

function continueLastActivity() {
    if (!_lastActivity) return;
    window.location.href = buildCopilotUrl(_lastActivity.id, _lastActivity.title, _lastActivity.project_name || '');
}

function showPlanSelector(event) {
    event.preventDefault();
    api.get('/api/copilot/stats')
        .then(function(data) {
            var plans = data.active_plans || [];
            if (!plans.length) {
                alert('Keine aktiven Plans vorhanden. Erstelle zuerst einen Plan unter /plans');
                return;
            }

            var choice = prompt('Plan-ID eingeben:\n\n' + plans.map(function(plan) {
                return plan.id + ': ' + plan.title;
            }).join('\n'));
            if (!choice) return;

            var selected = plans.find(function(plan) {
                return String(plan.id) === choice.trim();
            });
            window.location.href = buildCopilotUrl(
                choice.trim(),
                selected ? selected.title : ('Plan ' + choice.trim()),
                selected ? (selected.project_name || '') : ''
            );
        });
}

function slugifyPlanTitle(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'plan';
}

function buildCopilotUrl(planId, planTitle, projectName) {
    var url = '/copilot?plan_id=' + encodeURIComponent(planId) + '&plan=' + encodeURIComponent(slugifyPlanTitle(planTitle));
    if (projectName) url += '&project=' + encodeURIComponent(projectName);
    return url;
}
