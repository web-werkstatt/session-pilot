var allProjects = [];

function toggleQualityGuide(forceState) {
    var guide = document.getElementById('guideSection');
    var button = document.getElementById('qualityGuideToggle');
    if (!guide) return;
    var shouldShow = typeof forceState === 'boolean' ? forceState : guide.style.display === 'none';
    guide.style.display = shouldShow ? '' : 'none';
    if (button) button.innerHTML = '<i data-lucide="help-circle" class="icon icon-sm"></i> ' + (shouldShow ? 'Playbook ausblenden' : 'Playbook');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function loadProjects() {
    api.get('/api/quality/projects')
        .then(function(data) {
            allProjects = data;
            renderProjects(data);
            updateStats(data);
        })
        .catch(function() {
            document.getElementById('projectBody').innerHTML =
                '<tr><td colspan="7" class="loading-cell">No scanned projects found</td></tr>';
        });
}

function updateStats(projects) {
    document.getElementById('statProjects').textContent = projects.length;
    document.getElementById('statGood').textContent = projects.filter(function(p) { return p.score === 'A' || p.score === 'B'; }).length;
    document.getElementById('statMedium').textContent = projects.filter(function(p) { return p.score === 'C' || p.score === 'D'; }).length;
    document.getElementById('statBad').textContent = projects.filter(function(p) { return p.score === 'F'; }).length;
}

function scoreClass(score) {
    if (score === 'A' || score === 'B') return 'score-good';
    if (score === 'C' || score === 'D') return 'score-medium';
    return 'score-bad';
}

function qualityRisk(project) {
    if (!project) return { label: 'Unknown', cls: 'risk-neutral' };
    if ((project.errors || 0) > 0 || (project.score_numeric || 0) < 40) return { label: 'Critical', cls: 'risk-critical' };
    if ((project.warnings || 0) > 0 || (project.score_numeric || 0) < 60) return { label: 'Watch', cls: 'risk-watch' };
    return { label: 'Stable', cls: 'risk-stable' };
}

function qualityProjectPulse(project) {
    if (!project) return '';
    var parts = [];
    if ((project.errors || 0) > 0) parts.push(project.errors + ' blocker');
    if ((project.warnings || 0) > 0) parts.push(project.warnings + ' warnings');
    if (!parts.length) parts.push('No urgent issues');
    return parts.join(' · ');
}

function renderProjects(projects) {
    var tbody = document.getElementById('projectBody');
    if (!projects.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell"><div class="quality-empty"><strong>No quality reports yet.</strong><span>Start with a project scan to make this board useful.</span></div></td></tr>';
        return;
    }
    tbody.innerHTML = projects.map(function(p) {
        var risk = qualityRisk(p);
        return '<tr>' +
            '<td><div class="quality-project-cell"><a href="/project/' + encodeURIComponent(p.name) + '" class="project-link">' + escapeHtml(p.name) + '</a><span class="quality-project-meta">' + escapeHtml(qualityProjectPulse(p)) + '</span></div></td>' +
            '<td><span class="score-badge ' + scoreClass(p.score) + '">' + p.score + ' <small>' + p.score_numeric + '</small></span></td>' +
            '<td><span class="risk-pill ' + risk.cls + '">' + risk.label + '</span></td>' +
            '<td>' + (p.errors > 0 ? '<span class="count-error">' + p.errors + '</span>' : '<span class="count-zero">0</span>') + '</td>' +
            '<td>' + (p.warnings > 0 ? '<span class="count-warning">' + p.warnings + '</span>' : '<span class="count-zero">0</span>') + '</td>' +
            '<td><span class="quality-lastscan">' + formatTimeAgo(p.scanned_at) + '</span></td>' +
            '<td class="actions-cell">' +
                '<button class="btn btn-xs btn-secondary" onclick="showDetail(\'' + escapeHtml(p.name) + '\')">Details</button> ' +
                '<button class="btn btn-xs" onclick="scanSingle(\'' + escapeHtml(p.name) + '\')">Scan</button> ' +
                '<button class="btn btn-xs" onclick="setBaseline(\'' + escapeHtml(p.name) + '\')">Baseline</button>' +
            '</td>' +
        '</tr>';
    }).join('');
}

function showDetail(project) {
    document.getElementById('detailTitle').textContent = project;
    document.getElementById('detailBody').innerHTML = '<div class="loading-cell">Loading report...</div>';
    openModal('detailModal');

    api.get('/api/quality/report/' + encodeURIComponent(project))
        .then(function(data) {
            renderDetail(data);
        })
        .catch(function(err) {
            document.getElementById('detailBody').innerHTML = '<div class="loading-cell">Error: ' + err + '</div>';
        });
}

function renderDetail(data) {
    var r = data.report;
    var s = r.summary || {};
    var issues = r.issues || [];
    var risk = qualityRisk({
        score_numeric: r.score_numeric,
        errors: s.errors || 0,
        warnings: s.warnings || 0
    });

    var html = '<div class="detail-header">';
    html += '<div class="detail-score"><span class="score-badge score-lg ' + scoreClass(r.score) + '">' + r.score + '</span><span class="score-num">' + r.score_numeric + '/100</span><span class="risk-pill ' + risk.cls + '">' + risk.label + '</span></div>';
    html += '<div class="detail-stats">';
    html += '<span><strong>' + (s.errors || 0) + '</strong> Errors</span>';
    html += '<span><strong>' + (s.warnings || 0) + '</strong> Warnings</span>';
    html += '<span><strong>' + (s.info || 0) + '</strong> Info</span>';
    html += '<span><strong>' + (s.total_issues || 0) + '</strong> Total</span>';
    html += '</div>';

    if (data.diff) {
        var d = data.diff;
        html += '<div class="detail-diff">';
        html += '<span class="diff-label">Baseline diff</span>';
        html += '<span class="' + (d.score_delta >= 0 ? 'diff-good' : 'diff-bad') + '">Score ' + (d.score_delta >= 0 ? '+' : '') + d.score_delta + '</span>';
        if (d.new_issues > 0) html += '<span class="diff-bad">+' + d.new_issues + ' new</span>';
        if (d.fixed_issues > 0) html += '<span class="diff-good">' + d.fixed_issues + ' fixed</span>';
        html += '</div>';
    }
    html += '</div>';

    html += '<div class="detail-priority-strip">';
    html += '<div class="detail-priority-card"><span class="detail-priority-label">Focus now</span><strong>' + escapeHtml((s.errors || 0) > 0 ? 'Errors first' : ((s.warnings || 0) > 0 ? 'Warnings review' : 'Keep stable')) + '</strong></div>';
    html += '<div class="detail-priority-card"><span class="detail-priority-label">Recommended next step</span><strong>' + escapeHtml(data.diff ? 'Inspect diff before new baseline' : 'Create a baseline after review') + '</strong></div>';
    html += '</div>';

    // Issues nach Kategorie gruppieren
    var categories = {};
    issues.forEach(function(i) {
        if (i.status === 'ignored') return;
        var cat = i.category;
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push(i);
    });

    var catNames = {
        'duplication': 'Duplicates',
        'complexity': 'Complexity',
        'file_size': 'File Sizes',
        'css_tokens': 'CSS Quality',
        'css_undefined': 'CSS Variables',
        'architecture': 'Architecture',
        'test_failure': 'Tests',
        'js_quality': 'JS Quality'
    };

    Object.keys(categories).sort().forEach(function(cat) {
        var catIssues = categories[cat];
        var errors = catIssues.filter(function(i) { return i.level === 'error'; }).length;
        var warnings = catIssues.filter(function(i) { return i.level === 'warning'; }).length;
        var infos = catIssues.filter(function(i) { return i.level === 'info'; }).length;

        html += '<div class="issue-category">';
        html += '<div class="category-header" onclick="this.parentElement.classList.toggle(\'collapsed\')">';
        html += '<span class="category-name">' + (catNames[cat] || cat) + '</span>';
        html += '<span class="category-counts">';
        if (errors) html += '<span class="count-error">' + errors + ' E</span>';
        if (warnings) html += '<span class="count-warning">' + warnings + ' W</span>';
        if (infos) html += '<span class="count-info">' + infos + ' I</span>';
        html += '</span></div>';
        html += '<div class="category-issues">';

        catIssues.forEach(function(issue) {
            if (issue.level === 'info') return;
            var icon = issue.level === 'error' ? 'X' : '!';
            var cls = issue.level === 'error' ? 'issue-error' : 'issue-warning';
            html += '<div class="issue-item ' + cls + '">';
            html += '<span class="issue-icon">' + icon + '</span>';
            html += '<span class="issue-title">' + escapeHtml(issue.title) + '</span>';
            if (issue.files && issue.files.length) {
                html += '<span class="issue-files">' + issue.files.slice(0, 2).map(function(f) {
                    return f.split('/').pop();
                }).join(', ') + '</span>';
            }
            html += '</div>';
        });

        html += '</div></div>';
    });

    if (r.history && r.history.length > 1) {
        html += '<div class="history-section">';
        html += '<h4>Score History</h4>';
        html += '<div class="history-chart" id="historyChart"></div>';
        html += '</div>';
    }

    document.getElementById('detailBody').innerHTML = html;
}

function scanSingle(project) {
    var btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Scanning';

    api.post('/api/quality/scan/' + encodeURIComponent(project))
        .then(function() {
            btn.textContent = 'Done';
            setTimeout(function() { loadProjects(); }, 500);
        })
        .catch(function(err) {
            btn.textContent = 'Error';
            console.error(err);
        });
}

function scanProject() {
    var project = prompt('Enter project name (or leave empty for project_dashboard):');
    if (project === null) return;
    if (!project) project = 'project_dashboard';
    scanSingle(project);
}

function setBaseline(project) {
    if (!confirm('Set baseline for "' + project + '" to current state?')) return;

    api.post('/api/quality/baseline/' + encodeURIComponent(project))
        .then(function(data) {
            alert('Baseline set: ' + data.score + ' (' + data.score_numeric + '/100)');
            loadProjects();
        })
        .catch(function(err) {
            alert('Error: ' + err);
        });
}

document.addEventListener('DOMContentLoaded', loadProjects);
