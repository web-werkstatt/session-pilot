async function loadProjectOverviewCards() {
    var el = document.getElementById('projectOverviewCards');
    if (!el) return;

    try {
        var results = await Promise.all([
            api.get('/api/projects/' + encodeURIComponent(PROJECT_NAME) + '/planning').catch(function() { return {plans: []}; }),
            api.get('/api/quality/report/' + encodeURIComponent(PROJECT_NAME)).catch(function() { return {}; }),
            api.get('/api/sessions?project=' + encodeURIComponent(PROJECT_NAME) + '&limit=5').catch(function() { return {sessions: [], total: 0}; })
        ]);

        var planningData = results[0] || {};
        var qualityData = results[1] || {};
        var sessionData = results[2] || {};
        el.innerHTML = renderProjectOverviewCards(
            summarizeProjectPlanning(planningData.plans || []),
            summarizeProjectQuality(qualityData),
            summarizeProjectActivity(sessionData)
        );
    } catch (e) {
        el.innerHTML = '<div class="project-overview-empty">Project overview is currently unavailable.</div>';
    }
}

function summarizeProjectPlanning(planGroups) {
    var summary = {
        plans: planGroups.length,
        activePlans: 0,
        completedPlans: 0,
        sprintCount: 0,
        specCount: 0,
        directTaskCount: 0,
        markerCount: 0,
        doneMarkers: 0,
        reviewMarkers: 0,
        inProgressMarkers: 0,
        recentSprintTitles: []
    };

    planGroups.forEach(function(group) {
        var plan = group.plan || {};
        var stats = group.stats || {};
        var sprints = Array.isArray(group.sprints) ? group.sprints : [];

        if (plan.status === 'completed') summary.completedPlans += 1;
        else if (plan.status === 'active') summary.activePlans += 1;

        summary.sprintCount += stats.sprint_count || sprints.length || 0;
        summary.specCount += stats.spec_count || 0;
        summary.directTaskCount += stats.direct_task_count || 0;
        summary.markerCount += countPlanningMarkers(sprints);

        sprints.forEach(function(sprint) {
            if (summary.recentSprintTitles.length < 3 && sprint && sprint.title) {
                summary.recentSprintTitles.push(sprint.title);
            }
            countPlanningMarkerStatus(sprint, summary);
        });
    });

    summary.progressPercent = summary.markerCount
        ? Math.round((summary.doneMarkers / summary.markerCount) * 100)
        : 0;
    return summary;
}

function countPlanningMarkers(sprints) {
    var total = 0;
    (sprints || []).forEach(function(sprint) {
        total += Array.isArray(sprint.direct_markers) ? sprint.direct_markers.length : 0;
        (sprint.specs || []).forEach(function(spec) {
            total += Array.isArray(spec.markers) ? spec.markers.length : 0;
        });
    });
    return total;
}

function countPlanningMarkerStatus(sprint, summary) {
    var allMarkers = [];
    if (Array.isArray(sprint.direct_markers)) allMarkers = allMarkers.concat(sprint.direct_markers);
    (sprint.specs || []).forEach(function(spec) {
        if (Array.isArray(spec.markers)) allMarkers = allMarkers.concat(spec.markers);
    });

    allMarkers.forEach(function(marker) {
        var status = String((marker || {}).status || '').toLowerCase();
        if (status === 'done' || status === 'completed') summary.doneMarkers += 1;
        else if (status === 'review') summary.reviewMarkers += 1;
        else if (status === 'in_progress' || status === 'active') summary.inProgressMarkers += 1;
    });
}

function summarizeProjectQuality(data) {
    var report = data && data.report ? data.report : null;
    var diff = data && data.diff ? data.diff : null;
    var summary = report && report.summary ? report.summary : {};
    return {
        available: !!report,
        score: report ? (report.score || '-') : '-',
        totalIssues: summary.total_issues || 0,
        errors: summary.errors || 0,
        warnings: summary.warnings || 0,
        newIssues: diff ? (diff.new_issues || 0) : 0,
        fixedIssues: diff ? (diff.fixed_issues || 0) : 0
    };
}

function summarizeProjectActivity(data) {
    var sessions = Array.isArray(data.sessions) ? data.sessions : [];
    return {
        total: data && typeof data.total === 'number' ? data.total : sessions.length,
        recent: sessions.slice(0, 3),
        lastSession: sessions.length ? sessions[0] : null
    };
}

function renderProjectOverviewCards(planning, quality, activity) {
    var planningAction = buildPlanningAction(planning);
    var qualityAction = buildQualityAction(quality);
    var activityAction = buildActivityAction(activity);
    var detailAction = buildDetailAction(planning, quality, activity);
    var html = '';
    html += '<article class="project-overview-card project-overview-card--primary">';
    html += '<div class="project-overview-kicker">What Now</div>';
    html += '<h2 class="project-overview-title">' + escapeHtml(detailAction.title) + '</h2>';
    html += '<div class="project-overview-metric">' + escapeHtml(detailAction.metric) + '</div>';
    html += '<div class="project-overview-copy">' + escapeHtml(detailAction.copy) + '</div>';
    html += '<div class="project-overview-pills">';
    html += '<span class="project-overview-pill">' + escapeHtml(String(planning.plans)) + ' plans</span>';
    html += '<span class="project-overview-pill">' + escapeHtml(String(planning.sprintCount)) + ' sprint plans</span>';
    html += '<span class="project-overview-pill">' + escapeHtml(String(activity.total)) + ' sessions</span>';
    html += '</div>';
    html += renderProjectOverviewAction(detailAction.label, detailAction.href, detailAction.onclick, true);
    html += '</article>';

    html += '<article class="project-overview-card">';
    html += '<div class="project-overview-kicker">Planning</div>';
    html += '<h3 class="project-overview-card-title">' + escapeHtml(planningAction.title) + '</h3>';
    html += '<div class="project-overview-copy">' + escapeHtml(planningAction.copy) + '</div>';
    html += '<div class="project-overview-stat-grid">';
    html += renderProjectOverviewStat('Active plans', planning.activePlans);
    html += renderProjectOverviewStat('Sprint plans', planning.sprintCount);
    html += renderProjectOverviewStat('Mapped tasks', planning.markerCount);
    html += renderProjectOverviewStat('Progress', String(planning.progressPercent || 0) + '%');
    html += '</div>';
    html += '<div class="project-overview-list">';
    html += planning.recentSprintTitles.length
        ? planning.recentSprintTitles.map(function(title) { return '<div class="project-overview-list-item">' + escapeHtml(title) + '</div>'; }).join('')
        : '<div class="project-overview-empty-line">No sprint plans detected yet.</div>';
    html += '</div>';
    html += renderProjectOverviewAction(planningAction.label, planningAction.href, planningAction.onclick);
    html += '</article>';

    html += '<article class="project-overview-card">';
    html += '<div class="project-overview-kicker">Delivery</div>';
    html += '<h3 class="project-overview-card-title">' + escapeHtml(activityAction.deliveryTitle) + '</h3>';
    html += '<div class="project-overview-copy">' + escapeHtml(activityAction.deliveryCopy) + '</div>';
    html += '<div class="project-overview-stat-grid">';
    html += renderProjectOverviewStat('Done', planning.doneMarkers);
    html += renderProjectOverviewStat('In progress', planning.inProgressMarkers);
    html += renderProjectOverviewStat('In review', planning.reviewMarkers);
    html += renderProjectOverviewStat('Open work', Math.max(0, planning.markerCount - planning.doneMarkers));
    html += '</div>';
    html += renderProjectOverviewAction('Open Planning', '#', "switchProjectTabByName('plans'); return false;");
    html += '</article>';

    html += '<article class="project-overview-card">';
    html += '<div class="project-overview-kicker">Issues</div>';
    html += '<h3 class="project-overview-card-title">' + escapeHtml(qualityAction.title) + '</h3>';
    html += '<div class="project-overview-copy">' + escapeHtml(qualityAction.copy) + '</div>';
    if (!quality.available) {
        html += '<div class="project-overview-empty-line">No quality report available yet.</div>';
    } else {
        html += '<div class="project-overview-stat-grid">';
        html += renderProjectOverviewStat('New', quality.newIssues);
        html += renderProjectOverviewStat('Errors', quality.errors);
        html += renderProjectOverviewStat('Warnings', quality.warnings);
        html += renderProjectOverviewStat('Total', quality.totalIssues);
        html += '</div>';
        html += '<div class="project-overview-copy project-overview-copy--small">';
        html += quality.newIssues ? '<span class="project-overview-delta project-overview-delta--bad">+' + escapeHtml(String(quality.newIssues)) + ' new</span>' : '';
        html += quality.fixedIssues ? '<span class="project-overview-delta project-overview-delta--good">' + escapeHtml(String(quality.fixedIssues)) + ' fixed</span>' : '';
        if (!quality.newIssues && !quality.fixedIssues) html += 'No baseline diff available.';
        html += '</div>';
    }
    html += renderProjectOverviewAction(qualityAction.label, qualityAction.href, qualityAction.onclick);
    html += '</article>';

    html += '<article class="project-overview-card">';
    html += '<div class="project-overview-kicker">Activity</div>';
    html += '<h3 class="project-overview-card-title">' + escapeHtml(activityAction.title) + '</h3>';
    html += '<div class="project-overview-copy">' + escapeHtml(activityAction.copy) + '</div>';
    if (!activity.recent.length) {
        html += '<div class="project-overview-empty-line">No linked sessions yet.</div>';
    } else {
        html += '<div class="project-overview-list">';
        activity.recent.forEach(function(session) {
            html += '<a class="project-overview-session" href="/sessions/' + encodeURIComponent(session.session_uuid || '') + '">';
            html += '<span>' + escapeHtml(formatProjectOverviewSession(session)) + '</span>';
            html += '<span class="project-overview-session-model">' + escapeHtml(shortProjectOverviewModel(session.model)) + '</span>';
            html += '</a>';
        });
        html += '</div>';
    }
    html += renderProjectOverviewAction(activityAction.label, activityAction.href, activityAction.onclick);
    html += '</article>';
    return html;
}

function buildDetailAction(planning, quality, activity) {
    if (planning.inProgressMarkers > 0) {
        return {
            title: 'Continue active implementation',
            metric: String(planning.inProgressMarkers),
            copy: 'There is already active work in the plan hierarchy. Continue there instead of starting another parallel thread.',
            label: 'Open Planning',
            href: '#',
            onclick: "switchProjectTabByName('plans'); return false;"
        };
    }
    if (quality.newIssues > 0 || quality.errors > 0) {
        return {
            title: 'Resolve current blockers',
            metric: String(quality.newIssues || quality.errors),
            copy: 'The strongest current signal comes from open issues. Clear those before creating more delivery scope.',
            label: 'Open Quality',
            href: '#',
            onclick: "switchProjectTabByName('quality'); return false;"
        };
    }
    if (activity.lastSession && planning.markerCount > planning.doneMarkers) {
        return {
            title: 'Resume latest work context',
            metric: formatProjectOverviewSession(activity.lastSession),
            copy: 'There is unfinished mapped work and a recent session to continue from.',
            label: 'Open Activity',
            href: '#',
            onclick: "switchProjectTabByName('sessions'); return false;"
        };
    }
    return {
        title: 'Review project context',
        metric: String(planning.progressPercent || 0) + '%',
        copy: 'Use the detail view to re-check metadata, documents and README before deciding the next execution step.',
        label: 'Open Details',
        href: '#',
        onclick: "switchProjectTabByName('overview'); return false;"
    };
}

function buildPlanningAction(planning) {
    if (!planning.plans) {
        return {
            title: 'Create planning structure',
            copy: 'This project has no linked plan hierarchy yet. Start by creating or linking the first plan.',
            label: 'Open Planning',
            href: '#',
            onclick: "switchProjectTabByName('plans'); return false;"
        };
    }
    if (planning.inProgressMarkers > 0 || planning.reviewMarkers > 0) {
        return {
            title: 'Continue operative plan work',
            copy: 'There is already active or review work inside the sprint hierarchy. That should stay the primary execution lane.',
            label: 'Open Planning',
            href: '#',
            onclick: "switchProjectTabByName('plans'); return false;"
        };
    }
    return {
        title: 'Review sprint scope',
        copy: 'The structure exists, but the next step is to decide which sprint or mapped task should move next.',
        label: 'Open Planning',
        href: '#',
        onclick: "switchProjectTabByName('plans'); return false;"
    };
}

function buildQualityAction(quality) {
    if (!quality.available) {
        return {
            title: 'No issue baseline yet',
            copy: 'There is currently no quality report for this project. Run or inspect Quality before using issue counts as guidance.',
            label: 'Open Quality',
            href: '#',
            onclick: "switchProjectTabByName('quality'); return false;"
        };
    }
    if (quality.newIssues > 0 || quality.errors > 0) {
        return {
            title: 'Triage new issues first',
            copy: 'Fresh issues or hard errors are present. Those are the clearest blockers for stable delivery.',
            label: 'Open Quality',
            href: '#',
            onclick: "switchProjectTabByName('quality'); return false;"
        };
    }
    return {
        title: 'Quality looks stable',
        copy: 'No strong issue spike is visible right now. Use Quality mainly as a verification lane, not as the primary work entry.',
        label: 'Open Quality',
        href: '#',
        onclick: "switchProjectTabByName('quality'); return false;"
    };
}

function buildActivityAction(activity) {
    if (!activity.recent.length) {
        return {
            title: 'No recent execution context',
            copy: 'There are no linked sessions yet. The next useful context is likely in Planning or Details.',
            label: 'Open Details',
            href: '#',
            onclick: "switchProjectTabByName('overview'); return false;",
            deliveryTitle: 'Move work into execution',
            deliveryCopy: 'No recent activity is linked yet. Planning should define the next concrete work packet first.'
        };
    }
    return {
        title: 'Recent execution context exists',
        copy: 'Use recent sessions when you need the last working context before resuming delivery.',
        label: 'Open Activity',
        href: '#',
        onclick: "switchProjectTabByName('sessions'); return false;",
        deliveryTitle: 'Continue existing delivery flow',
        deliveryCopy: 'Mapped execution already exists. Prefer continuing open work over starting additional parallel tasks.'
    };
}

function renderProjectOverviewStat(label, value) {
    return '<div class="project-overview-stat"><div class="project-overview-stat-value">' + escapeHtml(String(value)) + '</div><div class="project-overview-stat-label">' + escapeHtml(label) + '</div></div>';
}

function renderProjectOverviewAction(label, href, onclick, primary) {
    var klass = primary ? 'project-overview-action project-overview-action--primary' : 'project-overview-action';
    var clickAttr = onclick ? ' onclick="' + onclick + '"' : '';
    return '<div class="project-overview-actions"><a class="' + klass + '" href="' + escapeHtml(href || '#') + '"' + clickAttr + '>' + escapeHtml(label) + '</a></div>';
}

function formatProjectOverviewSession(session) {
    if (!session || !session.started_at) return 'Session';
    var date = new Date(session.started_at);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ' · ' + (session.duration_formatted || session.duration_label || '-');
}

function shortProjectOverviewModel(model) {
    return String(model || '-')
        .replace('claude-', '')
        .replace('opus-4-6', 'Opus')
        .replace('sonnet-4-6', 'Sonnet');
}

function switchProjectTabByName(tab) {
    var target = document.querySelector(".project-tab[onclick*=\"'" + tab + "'\"]");
    if (target && typeof target.click === 'function') {
        target.click();
        return;
    }
    switchProjectTab(tab);
}
