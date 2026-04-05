let planningHierarchyData = [];
let planningSelectionId = '';

async function loadProjectPlans() {
    plansLoaded = true;
    try {
        const data = await api.get('/api/projects/' + encodeURIComponent(PROJECT_NAME) + '/planning');
        const planGroups = Array.isArray(data.plans) ? data.plans : [];
        planningHierarchyData = planGroups;
        planningSelectionId = '';
        const countEl = document.getElementById('plansCount');
        if (countEl && planGroups.length > 0) countEl.textContent = planGroups.length;

        if (!planGroups.length) {
            document.getElementById('plansBody').innerHTML = `
                <div style="text-align:center;padding:40px;color:#888">
                    <p>No plans assigned to this project yet.</p>
                    <a href="/plans" style="color:#0078d4">Open global plan index</a>
                </div>`;
            return;
        }
        document.getElementById('plansBody').innerHTML = renderPlanningWorkspace(planGroups);
    } catch(e) {
        document.getElementById('plansBody').innerHTML = '<p style="color:#ff6666;padding:20px">Error: ' + e + '</p>';
    }
}

function renderPlanningWorkspace(planGroups) {
    ensurePlanningSelection(planGroups);
    var html = ''
        + '<div class="planning-intro">'
        + '<div class="planning-intro-copy">'
        + '<div class="planning-kicker">Project workspace</div>'
        + '<div class="planning-title">Planning</div>'
        + '<div class="planning-subtitle">This view is the primary entry for plans in <strong>' + escapeHtml(PROJECT_NAME) + '</strong>. The global plan index remains a cross-project read view.</div>'
        + '</div>'
        + '<div class="planning-intro-actions">'
        + '<a href="/plans?project=' + encodeURIComponent(PROJECT_NAME) + '" class="planning-index-link">Open plan index</a>'
        + '</div>'
        + '</div>'
        + '<div class="planning-workspace">'
        + '<div class="planning-tree">';

    planGroups.forEach(function(group) {
        html += renderPlanHierarchyGroup(group);
    });

    html += '</div>'
        + '<aside class="planning-detail-panel" id="planningDetailPanel">'
        + renderPlanningDetailPanel()
        + '</aside>'
        + '</div>'
        + '<div class="planning-footer-link"><a href="/plans?project=' + encodeURIComponent(PROJECT_NAME) + '">Open project plans in global index &rarr;</a></div>';
    return html;
}

function projectPlanningStatusLabel(status) {
    var labels = { draft: 'Draft', active: 'Active', completed: 'Done', archived: 'Archive' };
    return labels[status] || status || 'Draft';
}

function buildProjectPlanningCopilotUrl(planId, planTitle) {
    return '/copilot?plan_id=' + encodeURIComponent(planId) + '&plan=' + encodeURIComponent(projectPlanningSlugify(planTitle)) + '&project=' + encodeURIComponent(PROJECT_NAME);
}

function projectPlanningSlugify(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'plan';
}

function renderPlanHierarchyGroup(group) {
    var plan = group.plan || {};
    var sprints = Array.isArray(group.sprints) ? group.sprints : [];
    var stats = group.stats || {};
    var detailUrl = '/plans/' + encodeURIComponent(plan.id) + '?project=' + encodeURIComponent(PROJECT_NAME) + '&from=project';

    var html = ''
        + '<section class="planning-plan-group">'
        + '<div class="planning-plan-head">'
        + '<div class="planning-plan-meta">'
        + '<div class="planning-plan-kicker">Plan</div>'
        + '<h3 class="planning-plan-name"><a href="' + detailUrl + '">' + escapeHtml(plan.title || 'Plan') + '</a></h3>'
        + '<div class="planning-plan-summary">' + escapeHtml(plan.summary || 'No summary available.') + '</div>'
        + '</div>'
        + '<div class="planning-plan-stats">'
        + '<span class="planning-pill">' + escapeHtml(projectPlanningStatusLabel(plan.status)) + '</span>'
        + '<span class="planning-pill">' + escapeHtml(String(stats.sprint_count || 0)) + ' sprints</span>'
        + '<span class="planning-pill">' + escapeHtml(String(stats.spec_count || 0)) + ' specs</span>'
        + '<span class="planning-pill">' + escapeHtml(String((stats.direct_task_count || 0) + (stats.direct_marker_count || 0))) + ' direct tasks</span>'
        + '</div>'
        + '</div>';

    if (!sprints.length) {
        html += '<div class="planning-empty">No sprint hierarchy detected in this plan yet.</div></section>';
        return html;
    }

    html += '<div class="planning-sprint-list">';
    sprints.forEach(function(sprint) {
        html += renderSprintHierarchyItem(plan, sprint);
    });
    html += '</div></section>';
    return html;
}

function renderSprintHierarchyItem(plan, sprint) {
    var specs = Array.isArray(sprint.specs) ? sprint.specs : [];
    var directTasks = Array.isArray(sprint.tasks) ? sprint.tasks : [];
    var directMarkers = Array.isArray(sprint.direct_markers) ? sprint.direct_markers : [];
    var sprintSessions = Array.isArray(sprint.sessions) ? sprint.sessions : [];
    var sprintId = buildPlanningNodeId('sprint', plan.id, sprint.id || sprint.sprint_tag || sprint.title);
    var html = ''
        + '<article class="planning-sprint-card planning-selectable' + (planningSelectionId === sprintId ? ' is-selected' : '') + '" onclick="selectPlanningNode(\'' + escapeJsValue(sprintId) + '\')">'
        + '<div class="planning-sprint-head">'
        + '<div>'
        + '<div class="planning-node-label">Sprint</div>'
        + '<div class="planning-sprint-title">' + escapeHtml(sprint.title || 'Sprint') + '</div>'
        + '</div>'
        + '<div class="planning-sprint-meta">'
        + '<span>' + escapeHtml(String(specs.length)) + ' specs</span>'
        + '<span>' + escapeHtml(String(directTasks.length + directMarkers.length)) + ' direct tasks</span>'
        + '<span>' + escapeHtml(String(sprintSessions.length)) + ' sessions</span>'
        + '</div>'
        + '</div>';

    if (specs.length) {
        html += '<div class="planning-spec-list">';
        specs.forEach(function(spec) {
            html += renderSpecHierarchyItem(plan, sprint, spec);
        });
        html += '</div>';
    }

    if (directTasks.length || directMarkers.length) {
        html += '<div class="planning-direct-block"><div class="planning-node-label">Direct sprint tasks</div>';
        html += renderTaskList(plan, sprint, null, directTasks, 'task');
        html += renderMarkerList(plan, sprint, null, directMarkers);
        html += '</div>';
    }

    html += '</article>';
    return html;
}

function renderSpecHierarchyItem(plan, sprint, spec) {
    var tasks = Array.isArray(spec.tasks) ? spec.tasks : [];
    var markers = Array.isArray(spec.markers) ? spec.markers : [];
    var sessions = Array.isArray(spec.sessions) ? spec.sessions : [];
    var specId = buildPlanningNodeId('spec', plan.id, sprint.id || sprint.sprint_tag || sprint.title, spec.id || spec.spec_tag || spec.title);
    var html = ''
        + '<div class="planning-spec-card planning-selectable' + (planningSelectionId === specId ? ' is-selected' : '') + '" onclick="selectPlanningNode(\'' + escapeJsValue(specId) + '\')">'
        + '<div class="planning-node-label">Spec</div>'
        + '<div class="planning-spec-title">' + escapeHtml(spec.title || 'Spec') + '</div>';

    if (spec.summary) html += '<div class="planning-spec-summary">' + escapeHtml(spec.summary) + '</div>';
    if (sessions.length) html += '<div class="planning-session-summary">' + escapeHtml(String(sessions.length)) + ' linked sessions</div>';

    html += renderTaskList(plan, sprint, spec, tasks, 'task');
    html += renderMarkerList(plan, sprint, spec, markers);
    html += '</div>';
    return html;
}

function renderTaskList(plan, sprint, spec, tasks, nodeType) {
    if (!tasks || !tasks.length) return '';
    return '<ul class="planning-task-list">' + tasks.map(function(task, index) {
        var taskTitle = getPlanningTaskTitle(task);
        var sessions = getPlanningTaskSessions(task);
        var taskId = buildPlanningNodeId(nodeType, plan.id, sprint.id || sprint.sprint_tag || sprint.title, spec ? (spec.id || spec.spec_tag || spec.title) : 'direct', index);
        return '<li class="planning-selectable' + (planningSelectionId === taskId ? ' is-selected' : '') + '" onclick="event.stopPropagation();selectPlanningNode(\'' + escapeJsValue(taskId) + '\')"><span class="planning-bullet-label">Task</span><span>' + escapeHtml(taskTitle) + '</span>' + (sessions.length ? '<span class="planning-session-chip">' + escapeHtml(String(sessions.length)) + ' session' + (sessions.length === 1 ? '' : 's') + '</span>' : '') + '</li>';
    }).join('') + '</ul>';
}

function renderMarkerList(plan, sprint, spec, markers) {
    if (!markers || !markers.length) return '';
    return '<ul class="planning-task-list">' + markers.map(function(marker) {
        var markerId = buildPlanningNodeId('marker', plan.id, sprint.id || sprint.sprint_tag || sprint.title, spec ? (spec.id || spec.spec_tag || spec.title) : 'direct', marker.marker_id || marker.titel);
        return '<li class="planning-selectable' + (planningSelectionId === markerId ? ' is-selected' : '') + '" onclick="event.stopPropagation();selectPlanningNode(\'' + escapeJsValue(markerId) + '\')"><span class="planning-bullet-label">Task</span><span>' + escapeHtml(marker.titel || marker.marker_id || 'Task') + '</span><span class="planning-marker-status">' + escapeHtml(marker.status || 'todo') + '</span></li>';
    }).join('') + '</ul>';
}

function ensurePlanningSelection(planGroups) {
    if (planningSelectionId && findPlanningNodeById(planningSelectionId)) return;
    planningSelectionId = '';
    for (var i = 0; i < planGroups.length; i++) {
        var first = findFirstPlanningSelection(planGroups[i]);
        if (first) {
            planningSelectionId = first.id;
            return;
        }
    }
}

function findFirstPlanningSelection(group) {
    var plan = group.plan || {};
    var sprints = Array.isArray(group.sprints) ? group.sprints : [];
    for (var i = 0; i < sprints.length; i++) {
        var sprint = sprints[i];
        var specs = Array.isArray(sprint.specs) ? sprint.specs : [];
        for (var j = 0; j < specs.length; j++) {
            var spec = specs[j];
            var markers = Array.isArray(spec.markers) ? spec.markers : [];
            if (markers.length) return { id: buildPlanningNodeId('marker', plan.id, sprint.id || sprint.sprint_tag || sprint.title, spec.id || spec.spec_tag || spec.title, markers[0].marker_id || markers[0].titel) };
            var tasks = Array.isArray(spec.tasks) ? spec.tasks : [];
            if (tasks.length) return { id: buildPlanningNodeId('task', plan.id, sprint.id || sprint.sprint_tag || sprint.title, spec.id || spec.spec_tag || spec.title, 0) };
            return { id: buildPlanningNodeId('spec', plan.id, sprint.id || sprint.sprint_tag || sprint.title, spec.id || spec.spec_tag || spec.title) };
        }
        var directMarkers = Array.isArray(sprint.direct_markers) ? sprint.direct_markers : [];
        if (directMarkers.length) return { id: buildPlanningNodeId('marker', plan.id, sprint.id || sprint.sprint_tag || sprint.title, 'direct', directMarkers[0].marker_id || directMarkers[0].titel) };
        var directTasks = Array.isArray(sprint.tasks) ? sprint.tasks : [];
        if (directTasks.length) return { id: buildPlanningNodeId('task', plan.id, sprint.id || sprint.sprint_tag || sprint.title, 'direct', 0) };
        return { id: buildPlanningNodeId('sprint', plan.id, sprint.id || sprint.sprint_tag || sprint.title) };
    }
    return null;
}

function buildPlanningNodeId() {
    return Array.prototype.slice.call(arguments).map(function(part) {
        return String(part || '').replace(/[|]/g, '-');
    }).join('|');
}

function escapeJsValue(value) {
    return String(value || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function selectPlanningNode(nodeId) {
    planningSelectionId = nodeId;
    var body = document.getElementById('plansBody');
    if (body) body.innerHTML = renderPlanningWorkspace(planningHierarchyData);
}

function renderPlanningDetailPanel() {
    var match = findPlanningNodeById(planningSelectionId);
    if (!match) return '<div class="planning-detail-empty">Select a spec or task to inspect the operative details.</div>';

    var context = '<div class="planning-detail-kicker">' + escapeHtml(match.kindLabel) + '</div>'
        + '<h3 class="planning-detail-title">' + escapeHtml(match.title) + '</h3>'
        + '<div class="planning-detail-path">' + escapeHtml(match.path.join(' / ')) + '</div>';

    if (match.kind === 'marker') return context + renderMarkerDetail(match);
    if (match.kind === 'session') return context + renderSessionDetail(match);
    if (match.kind === 'task') return context + renderTaskDetail(match);
    if (match.kind === 'spec') return context + renderSpecDetail(match);
    return context + renderSprintDetail(match);
}

function renderMarkerDetail(match) {
    var marker = match.marker || {};
    var checks = Array.isArray(marker.checks) ? marker.checks : [];
    var prompt = marker.prompt || marker.prompt_suggestion || '';
    var sessions = match.sessions || [];
    var fallbackSessions = getPlanningFallbackSessions(match);
    return ''
        + renderDetailField('Status', marker.status || '-')
        + renderDetailField('Goal', marker.ziel || '-')
        + renderDetailField('Next Step', marker.naechster_schritt || '-')
        + renderDetailField('Risk', marker.risiko || '-')
        + renderDetailField('Last Session', marker.last_session || '-')
        + renderDetailBlock('Checks', checks.length ? '<ul class="planning-detail-list">' + checks.map(function(item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('') + '</ul>' : '<div class="planning-detail-muted">No checks defined.</div>')
        + renderDetailBlock('Prompt', prompt ? '<pre class="planning-detail-pre">' + escapeHtml(prompt) + '</pre>' : '<div class="planning-detail-muted">No prompt defined.</div>')
        + renderDetailBlock('Sessions', renderSessionHistory(sessions, match.path))
        + renderRecentProjectSessionsBlock(fallbackSessions, match.path, sessions.length)
        + renderDetailActions(match.plan);
}

function renderTaskDetail(match) {
    var sessions = match.sessions || [];
    var fallbackSessions = getPlanningFallbackSessions(match);
    return ''
        + renderDetailField('Status', 'planned')
        + renderDetailField('Goal', match.taskTitle || '-')
        + renderDetailField('Next Step', sessions.length ? 'Use the linked session history to continue this task in context.' : 'Turn this task into a marker or continue via Copilot.')
        + renderDetailField('Risk', '-')
        + renderDetailBlock('Checks', '<div class="planning-detail-muted">No checks stored for plain markdown tasks.</div>')
        + renderDetailBlock('Prompt', '<div class="planning-detail-muted">No prompt stored for plain markdown tasks.</div>')
        + renderDetailBlock('Sessions', renderSessionHistory(sessions, match.path))
        + renderRecentProjectSessionsBlock(fallbackSessions, match.path, sessions.length)
        + renderDetailActions(match.plan);
}

function renderSpecDetail(match) {
    var spec = match.spec || {};
    var taskCount = Array.isArray(spec.tasks) ? spec.tasks.length : 0;
    var markerCount = Array.isArray(spec.markers) ? spec.markers.length : 0;
    var sessions = match.sessions || [];
    var fallbackSessions = getPlanningFallbackSessions(match);
    return ''
        + renderDetailField('Summary', spec.summary || '-')
        + renderDetailField('Tasks', String(taskCount))
        + renderDetailField('Mapped Tasks', String(markerCount))
        + renderDetailField('Linked Sessions', String(sessions.length))
        + renderDetailBlock('Contained Work', taskCount || markerCount ? buildSpecWorkSummary(spec) : '<div class="planning-detail-muted">No task content stored yet.</div>')
        + renderDetailBlock('Sessions', renderSessionHistory(sessions, match.path))
        + renderRecentProjectSessionsBlock(fallbackSessions, match.path, sessions.length)
        + renderDetailActions(match.plan);
}

function renderSprintDetail(match) {
    var sprint = match.sprint || {};
    var sessions = match.sessions || [];
    var fallbackSessions = getPlanningFallbackSessions(match);
    return ''
        + renderDetailField('Summary', sprint.summary || '-')
        + renderDetailField('Sprint Tag', sprint.sprint_tag || '-')
        + renderDetailField('Plan ID', sprint.plan_id || '-')
        + renderDetailField('Linked Sessions', String(sessions.length))
        + renderDetailBlock('Next Step', '<div class="planning-detail-muted">Select a spec or task inside this sprint for operative work.</div>')
        + renderDetailBlock('Sessions', renderSessionHistory(sessions, match.path))
        + renderRecentProjectSessionsBlock(fallbackSessions, match.path, sessions.length)
        + renderDetailActions(match.plan);
}

function renderSessionDetail(match) {
    var session = match.session || {};
    return ''
        + renderDetailField('Started', formatPlanningDate(session.started_at) || '-')
        + renderDetailField('Duration', session.duration_label || '-')
        + renderDetailField('Model', session.model || '-')
        + renderDetailField('Outcome', session.outcome || 'unrated')
        + renderDetailField('Session UUID', session.session_uuid || '-')
        + '<div class="planning-detail-actions"><a class="planning-detail-btn" href="/sessions/' + encodeURIComponent(session.session_uuid || '') + '">Open Session Detail</a></div>';
}

function buildSpecWorkSummary(spec) {
    var html = '';
    if (Array.isArray(spec.tasks) && spec.tasks.length) {
        html += '<div class="planning-detail-subhead">Tasks</div><ul class="planning-detail-list">' + spec.tasks.map(function(task) { return '<li>' + escapeHtml(getPlanningTaskTitle(task)) + '</li>'; }).join('') + '</ul>';
    }
    if (Array.isArray(spec.markers) && spec.markers.length) {
        html += '<div class="planning-detail-subhead">Mapped Tasks</div><ul class="planning-detail-list">' + spec.markers.map(function(marker) { return '<li>' + escapeHtml(marker.titel || marker.marker_id || 'Task') + '</li>'; }).join('') + '</ul>';
    }
    return html;
}

function renderDetailField(label, value) {
    return '<div class="planning-detail-field"><div class="planning-detail-label">' + escapeHtml(label) + '</div><div class="planning-detail-value">' + escapeHtml(value) + '</div></div>';
}

function renderDetailBlock(label, content) {
    return '<div class="planning-detail-block"><div class="planning-detail-label">' + escapeHtml(label) + '</div>' + content + '</div>';
}

function renderDetailActions(plan) {
    var planId = plan && plan.id ? plan.id : '';
    var planTitle = plan && plan.title ? plan.title : 'plan';
    return '<div class="planning-detail-actions"><a class="planning-detail-btn" href="' + buildProjectPlanningCopilotUrl(planId, planTitle) + '">Open in Copilot</a><a class="planning-detail-btn planning-detail-btn-secondary" href="/plans/' + encodeURIComponent(planId) + '?project=' + encodeURIComponent(PROJECT_NAME) + '&from=project">Open Plan Detail</a></div>';
}

function renderSessionHistory(sessions, path) {
    var items = Array.isArray(sessions) ? sessions : [];
    if (!items.length) {
        return '<div class="planning-detail-muted">No sessions linked yet. Continue the work via Copilot to create execution history on the operative level.</div>';
    }
    return '<div class="planning-session-history">' + items.map(function(session) {
        var sessionUrl = '/sessions/' + encodeURIComponent(session.session_uuid || '');
        return '<a class="planning-session-item planning-session-link" href="' + sessionUrl + '"><span class="planning-session-main">' + escapeHtml(formatPlanningDate(session.started_at) || (session.session_uuid || 'Session')) + '</span><span class="planning-session-meta">' + escapeHtml(session.model || 'unknown model') + ' • ' + escapeHtml(session.duration_label || '-') + ' • ' + escapeHtml(session.outcome || 'unrated') + '</span></a>';
    }).join('') + '</div>';
}

function getPlanningTaskTitle(task) {
    if (task && typeof task === 'object') return task.title || task.titel || 'Task';
    return String(task || 'Task');
}

function getPlanningTaskSessions(task) {
    if (task && typeof task === 'object' && Array.isArray(task.sessions)) return task.sessions;
    return [];
}

function getPlanningFallbackSessions(match) {
    if (!match || !Array.isArray(match.projectSessions)) return [];
    if (Array.isArray(match.sessions) && match.sessions.length) return [];
    return match.projectSessions.slice(0, 5);
}

function renderRecentProjectSessionsBlock(sessions, path, linkedCount) {
    var items = Array.isArray(sessions) ? sessions : [];
    if (!items.length) return '';
    var intro = linkedCount ? 'Additional recent project sessions:' : 'No direct task/spec link exists yet. Recent project sessions:';
    return renderDetailBlock('Recent Project Sessions', '<div class="planning-detail-muted">' + escapeHtml(intro) + '</div>' + renderSessionHistory(items, path));
}

function buildPlanningSessionNodeId(path, sessionUuid) {
    return buildPlanningNodeId('session', (path || []).join('>'), sessionUuid || '');
}

function formatPlanningDate(value) {
    if (!value) return '';
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    return date.toLocaleString();
}

function findPlanningNodeById(nodeId) {
    if (!nodeId) return null;
    for (var i = 0; i < planningHierarchyData.length; i++) {
        var group = planningHierarchyData[i];
        var plan = group.plan || {};
        var sprints = Array.isArray(group.sprints) ? group.sprints : [];
        for (var j = 0; j < sprints.length; j++) {
            var sprint = sprints[j];
            var sprintKey = sprint.id || sprint.sprint_tag || sprint.title;
            var sprintPath = [plan.title || 'Plan', sprint.title || 'Sprint'];
            if (nodeId === buildPlanningNodeId('sprint', plan.id, sprintKey)) return { kind: 'sprint', kindLabel: 'Sprint', title: sprint.title || 'Sprint', path: sprintPath, plan: plan, sprint: sprint, sessions: Array.isArray(sprint.sessions) ? sprint.sessions : [], projectSessions: Array.isArray(group.recent_sessions) ? group.recent_sessions : [] };

            var specs = Array.isArray(sprint.specs) ? sprint.specs : [];
            for (var k = 0; k < specs.length; k++) {
                var spec = specs[k];
                var specKey = spec.id || spec.spec_tag || spec.title;
                var specPath = [plan.title || 'Plan', sprint.title || 'Sprint', spec.title || 'Spec'];
                if (nodeId === buildPlanningNodeId('spec', plan.id, sprintKey, specKey)) return { kind: 'spec', kindLabel: 'Spec', title: spec.title || 'Spec', path: specPath, plan: plan, sprint: sprint, spec: spec, sessions: Array.isArray(spec.sessions) ? spec.sessions : [], projectSessions: Array.isArray(group.recent_sessions) ? group.recent_sessions : [] };

                var specTasks = Array.isArray(spec.tasks) ? spec.tasks : [];
                for (var t = 0; t < specTasks.length; t++) {
                    var specTaskTitle = getPlanningTaskTitle(specTasks[t]);
                    var specTaskPath = [plan.title || 'Plan', sprint.title || 'Sprint', spec.title || 'Spec', specTaskTitle];
                    if (nodeId === buildPlanningNodeId('task', plan.id, sprintKey, specKey, t)) return { kind: 'task', kindLabel: 'Task', title: specTaskTitle, taskTitle: specTaskTitle, path: specTaskPath, plan: plan, sprint: sprint, spec: spec, sessions: getPlanningTaskSessions(specTasks[t]), projectSessions: Array.isArray(group.recent_sessions) ? group.recent_sessions : [] };
                }

                var specMarkers = Array.isArray(spec.markers) ? spec.markers : [];
                for (var m = 0; m < specMarkers.length; m++) {
                    var specMarker = specMarkers[m];
                    var specMarkerPath = [plan.title || 'Plan', sprint.title || 'Sprint', spec.title || 'Spec', specMarker.titel || specMarker.marker_id || 'Task'];
                    if (nodeId === buildPlanningNodeId('marker', plan.id, sprintKey, specKey, specMarker.marker_id || specMarker.titel)) return { kind: 'marker', kindLabel: 'Task', title: specMarker.titel || specMarker.marker_id || 'Task', path: specMarkerPath, plan: plan, sprint: sprint, spec: spec, marker: specMarker, sessions: Array.isArray(specMarker.sessions) ? specMarker.sessions : [], projectSessions: Array.isArray(group.recent_sessions) ? group.recent_sessions : [] };
                }
            }

            var directTasks = Array.isArray(sprint.tasks) ? sprint.tasks : [];
            for (var dt = 0; dt < directTasks.length; dt++) {
                var directTaskTitle = getPlanningTaskTitle(directTasks[dt]);
                var directTaskPath = [plan.title || 'Plan', sprint.title || 'Sprint', directTaskTitle];
                if (nodeId === buildPlanningNodeId('task', plan.id, sprintKey, 'direct', dt)) return { kind: 'task', kindLabel: 'Task', title: directTaskTitle, taskTitle: directTaskTitle, path: directTaskPath, plan: plan, sprint: sprint, sessions: getPlanningTaskSessions(directTasks[dt]), projectSessions: Array.isArray(group.recent_sessions) ? group.recent_sessions : [] };
            }

            var directMarkers = Array.isArray(sprint.direct_markers) ? sprint.direct_markers : [];
            for (var dm = 0; dm < directMarkers.length; dm++) {
                var directMarker = directMarkers[dm];
                var directMarkerPath = [plan.title || 'Plan', sprint.title || 'Sprint', directMarker.titel || directMarker.marker_id || 'Task'];
                if (nodeId === buildPlanningNodeId('marker', plan.id, sprintKey, 'direct', directMarker.marker_id || directMarker.titel)) return { kind: 'marker', kindLabel: 'Task', title: directMarker.titel || directMarker.marker_id || 'Task', path: directMarkerPath, plan: plan, sprint: sprint, marker: directMarker, sessions: Array.isArray(directMarker.sessions) ? directMarker.sessions : [], projectSessions: Array.isArray(group.recent_sessions) ? group.recent_sessions : [] };
            }

            var sessionMatch = findPlanningSessionMatch(nodeId, sprintPath, sprint.sessions, plan, sprint, null, null);
            if (sessionMatch) return sessionMatch;
            for (var sp = 0; sp < specs.length; sp++) {
                var loopSpec = specs[sp];
                var loopSpecPath = [plan.title || 'Plan', sprint.title || 'Sprint', loopSpec.title || 'Spec'];
                sessionMatch = findPlanningSessionMatch(nodeId, loopSpecPath, loopSpec.sessions, plan, sprint, loopSpec, null);
                if (sessionMatch) return sessionMatch;
                var loopTasks = Array.isArray(loopSpec.tasks) ? loopSpec.tasks : [];
                for (var st = 0; st < loopTasks.length; st++) {
                    var loopTaskTitle = getPlanningTaskTitle(loopTasks[st]);
                    sessionMatch = findPlanningSessionMatch(nodeId, loopSpecPath.concat([loopTaskTitle]), getPlanningTaskSessions(loopTasks[st]), plan, sprint, loopSpec, { title: loopTaskTitle });
                    if (sessionMatch) return sessionMatch;
                }
                var loopMarkers = Array.isArray(loopSpec.markers) ? loopSpec.markers : [];
                for (var sm = 0; sm < loopMarkers.length; sm++) {
                    var loopSpecMarker = loopMarkers[sm];
                    sessionMatch = findPlanningSessionMatch(nodeId, loopSpecPath.concat([loopSpecMarker.titel || loopSpecMarker.marker_id || 'Task']), loopSpecMarker.sessions, plan, sprint, loopSpec, null, loopSpecMarker);
                    if (sessionMatch) return sessionMatch;
                }
            }
            for (var dts = 0; dts < directTasks.length; dts++) {
                var loopDirectTaskTitle = getPlanningTaskTitle(directTasks[dts]);
                sessionMatch = findPlanningSessionMatch(nodeId, sprintPath.concat([loopDirectTaskTitle]), getPlanningTaskSessions(directTasks[dts]), plan, sprint, null, { title: loopDirectTaskTitle });
                if (sessionMatch) return sessionMatch;
            }
            for (var dms = 0; dms < directMarkers.length; dms++) {
                var loopDirectMarker = directMarkers[dms];
                sessionMatch = findPlanningSessionMatch(nodeId, sprintPath.concat([loopDirectMarker.titel || loopDirectMarker.marker_id || 'Task']), loopDirectMarker.sessions, plan, sprint, null, null, loopDirectMarker);
                if (sessionMatch) return sessionMatch;
            }
        }
    }
    return null;
}

function findPlanningSessionMatch(nodeId, path, sessions, plan, sprint, spec, task, marker) {
    var items = Array.isArray(sessions) ? sessions : [];
    for (var i = 0; i < items.length; i++) {
        var session = items[i];
        if (nodeId === buildPlanningSessionNodeId(path, session.session_uuid)) {
            return { kind: 'session', kindLabel: 'Session', title: formatPlanningDate(session.started_at) || session.session_uuid || 'Session', path: (path || []).concat(['Session']), plan: plan, sprint: sprint, spec: spec, task: task, marker: marker, session: session };
        }
    }
    return null;
}
