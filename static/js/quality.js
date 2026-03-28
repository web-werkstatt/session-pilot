var allProjects = [];

function loadProjects() {
    api.get('/api/quality/projects')
        .then(function(data) {
            allProjects = data;
            renderProjects(data);
            updateStats(data);
        })
        .catch(function() {
            document.getElementById('projectBody').innerHTML =
                '<tr><td colspan="7" class="loading-cell">Keine gescannten Projekte gefunden</td></tr>';
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

function renderProjects(projects) {
    var tbody = document.getElementById('projectBody');
    if (!projects.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Noch keine Projekte gescannt. Klicke "Scan" um zu starten.</td></tr>';
        return;
    }
    tbody.innerHTML = projects.map(function(p) {
        return '<tr>' +
            '<td><a href="#" onclick="showDetail(\'' + escapeHtml(p.name) + '\'); return false;" class="project-link">' + escapeHtml(p.name) + '</a></td>' +
            '<td><span class="score-badge ' + scoreClass(p.score) + '">' + p.score + ' <small>' + p.score_numeric + '</small></span></td>' +
            '<td>' + (p.errors > 0 ? '<span class="count-error">' + p.errors + '</span>' : '<span class="count-zero">0</span>') + '</td>' +
            '<td>' + (p.warnings > 0 ? '<span class="count-warning">' + p.warnings + '</span>' : '<span class="count-zero">0</span>') + '</td>' +
            '<td>' + (p.info > 0 ? p.info : '<span class="count-zero">0</span>') + '</td>' +
            '<td>' + formatTimeAgo(p.scanned_at) + '</td>' +
            '<td class="actions-cell">' +
                '<button class="btn btn-xs" onclick="scanSingle(\'' + escapeHtml(p.name) + '\')">Scan</button> ' +
                '<button class="btn btn-xs" onclick="setBaseline(\'' + escapeHtml(p.name) + '\')">Baseline</button>' +
            '</td>' +
        '</tr>';
    }).join('');
}

function showDetail(project) {
    document.getElementById('detailTitle').textContent = project;
    document.getElementById('detailBody').innerHTML = '<div class="loading-cell">Lade Report...</div>';
    openModal('detailModal');

    api.get('/api/quality/report/' + encodeURIComponent(project))
        .then(function(data) {
            renderDetail(data);
        })
        .catch(function(err) {
            document.getElementById('detailBody').innerHTML = '<div class="loading-cell">Fehler: ' + err + '</div>';
        });
}

function renderDetail(data) {
    var r = data.report;
    var s = r.summary || {};
    var issues = r.issues || [];

    var html = '<div class="detail-header">';
    html += '<div class="detail-score"><span class="score-badge score-lg ' + scoreClass(r.score) + '">' + r.score + '</span><span class="score-num">' + r.score_numeric + '/100</span></div>';
    html += '<div class="detail-stats">';
    html += '<span>' + (s.errors || 0) + ' Errors</span>';
    html += '<span>' + (s.warnings || 0) + ' Warnings</span>';
    html += '<span>' + (s.info || 0) + ' Info</span>';
    html += '</div>';

    if (data.diff) {
        var d = data.diff;
        html += '<div class="detail-diff">';
        html += '<span class="diff-label">vs. Baseline:</span>';
        html += '<span class="' + (d.score_delta >= 0 ? 'diff-good' : 'diff-bad') + '">Score ' + (d.score_delta >= 0 ? '+' : '') + d.score_delta + '</span>';
        if (d.new_issues > 0) html += '<span class="diff-bad">+' + d.new_issues + ' neu</span>';
        if (d.fixed_issues > 0) html += '<span class="diff-good">' + d.fixed_issues + ' behoben</span>';
        html += '</div>';
    }
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
        'duplication': 'Duplikate',
        'complexity': 'Komplexitaet',
        'file_size': 'Dateigroessen',
        'css_tokens': 'CSS-Qualitaet',
        'css_undefined': 'CSS-Variablen',
        'architecture': 'Architektur',
        'test_failure': 'Tests',
        'js_quality': 'JS-Qualitaet'
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
        html += '<h4>Score-Verlauf</h4>';
        html += '<div class="history-chart" id="historyChart"></div>';
        html += '</div>';
    }

    document.getElementById('detailBody').innerHTML = html;
}

function scanSingle(project) {
    var btn = event.target;
    btn.disabled = true;
    btn.textContent = '...';

    api.post('/api/quality/scan/' + encodeURIComponent(project))
        .then(function() {
            btn.textContent = 'OK';
            setTimeout(function() { loadProjects(); }, 500);
        })
        .catch(function(err) {
            btn.textContent = 'Fehler';
            console.error(err);
        });
}

function scanProject() {
    var project = prompt('Projektname eingeben (oder leer fuer project_dashboard):');
    if (project === null) return;
    if (!project) project = 'project_dashboard';
    scanSingle(project);
}

function setBaseline(project) {
    if (!confirm('Baseline fuer "' + project + '" auf aktuellen Stand setzen?')) return;

    api.post('/api/quality/baseline/' + encodeURIComponent(project))
        .then(function(data) {
            alert('Baseline gesetzt: ' + data.score + ' (' + data.score_numeric + '/100)');
            loadProjects();
        })
        .catch(function(err) {
            alert('Fehler: ' + err);
        });
}

document.addEventListener('DOMContentLoaded', loadProjects);
