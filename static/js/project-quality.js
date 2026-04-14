/**
 * Project Detail — Quality Tab
 * Extrahiert aus project-detail.js (Dateigroessen-Limit).
 * Erwartet: PROJECT_NAME, api, escapeHtml, setQualityButtonState, loadQualityButtonState, qualityLoaded
 */

// === Quality Tab ===
async function loadQualityTab() {
    qualityLoaded = true;
    var body = document.getElementById('qualityBody');
    try {
        var d = await api.get('/api/quality/report/' + encodeURIComponent(PROJECT_NAME));
        var r = d.report;
        if (!r) {
            body.innerHTML = '<div style="text-align:center;padding:40px;color:#888"><p>No quality report available.</p><button class="btn btn-primary btn-sm" onclick="runQualityScan()">Scan now</button></div>';
            return;
        }

        var s = r.summary || {};
        var scoreColors = { A: '#43a047', B: '#43a047', C: '#ffc107', D: '#ffc107', F: '#f44336' };
        var scoreColor = scoreColors[r.score] || '#f44336';

        var html = '<div style="display:flex;align-items:center;gap:20px;margin-bottom:20px;flex-wrap:wrap">';
        html += '<div style="text-align:center"><span style="font-size:48px;font-weight:700;color:' + scoreColor + '">' + r.score + '</span><div style="color:#888;font-size:13px">' + r.score_numeric + '/100</div></div>';
        html += '<div style="display:flex;gap:20px">';
        html += '<div style="text-align:center"><span style="font-size:20px;font-weight:600;color:#f44336">' + (s.errors || 0) + '</span><div style="font-size:11px;color:#888">Errors</div></div>';
        html += '<div style="text-align:center"><span style="font-size:20px;font-weight:600;color:#ffc107">' + (s.warnings || 0) + '</span><div style="font-size:11px;color:#888">Warnings</div></div>';
        html += '<div style="text-align:center"><span style="font-size:20px;font-weight:600;color:#888">' + (s.info || 0) + '</span><div style="font-size:11px;color:#888">Info</div></div>';
        html += '</div>';

        if (d.diff) {
            var delta = d.diff.score_delta;
            html += '<div style="padding:8px 14px;background:var(--bg-card);border-radius:6px;font-size:12px">';
            html += '<div style="color:#888;margin-bottom:4px">vs. Baseline</div>';
            html += '<span style="color:' + (delta >= 0 ? '#43a047' : '#f44336') + ';font-weight:600">Score ' + (delta >= 0 ? '+' : '') + delta + '</span>';
            if (d.diff.new_issues > 0) html += ' <span style="color:#f44336">+' + d.diff.new_issues + ' new</span>';
            if (d.diff.fixed_issues > 0) html += ' <span style="color:#43a047">' + d.diff.fixed_issues + ' fixed</span>';
            html += '</div>';
        }

        html += '<div style="margin-left:auto;display:flex;gap:8px">';
        html += '<button class="btn btn-sm" onclick="runQualityScan()">Re-scan</button>';
        html += '<button class="btn btn-sm" onclick="setProjectBaseline()">Set baseline</button>';
        html += '</div>';
        html += '</div>';

        // Issues nach Kategorie
        var categories = {};
        (r.issues || []).forEach(function(i) {
            if (i.status === 'ignored') return;
            if (!categories[i.category]) categories[i.category] = [];
            categories[i.category].push(i);
        });

        var catNames = { duplication: 'Duplicates', complexity: 'Complexity', file_size: 'File Sizes', css_tokens: 'CSS Quality', css_undefined: 'CSS Variables', architecture: 'Architecture', test_failure: 'Tests', js_quality: 'JS Quality' };

        Object.keys(categories).sort().forEach(function(cat) {
            var items = categories[cat];
            var errors = items.filter(function(i) { return i.level === 'error'; }).length;
            var warnings = items.filter(function(i) { return i.level === 'warning'; }).length;
            var infos = items.filter(function(i) { return i.level === 'info'; }).length;

            html += '<div style="margin-bottom:8px;border:1px solid var(--border);border-radius:6px;overflow:hidden">';
            html += '<div style="display:flex;justify-content:space-between;padding:10px 14px;background:var(--bg-card);cursor:pointer" onclick="this.parentElement.classList.toggle(\'q-collapsed\')">';
            html += '<span style="font-weight:600;font-size:13px">' + (catNames[cat] || cat) + '</span>';
            html += '<span style="font-size:12px">';
            if (errors) html += '<span style="color:#f44336;margin-right:8px">' + errors + ' E</span>';
            if (warnings) html += '<span style="color:#ffc107;margin-right:8px">' + warnings + ' W</span>';
            if (infos) html += '<span style="color:#888">' + infos + ' I</span>';
            html += '</span></div>';
            html += '<div class="q-issues">';

            items.forEach(function(issue) {
                if (issue.level === 'info') return;
                var color = issue.level === 'error' ? '#f44336' : '#ffc107';
                var icon = issue.level === 'error' ? 'X' : '!';
                html += '<div style="display:flex;align-items:center;gap:8px;padding:5px 14px;font-size:12px;border-top:1px solid var(--border)">';
                html += '<span style="color:' + color + ';font-weight:700;width:14px;text-align:center">' + icon + '</span>';
                html += '<span style="flex:1;color:#ccc">' + escapeHtml(issue.title) + '</span>';
                if (issue.files && issue.files.length) html += '<span style="color:#666;font-size:11px">' + issue.files.slice(0, 2).map(function(f) { return f.split('/').pop(); }).join(', ') + '</span>';
                html += '</div>';
            });
            html += '</div></div>';
        });

        html += '<style>.q-collapsed .q-issues { display: none; }</style>';
        body.innerHTML = html;
    } catch(e) {
        body.innerHTML = '<div style="text-align:center;padding:40px;color:#888"><p>No quality report available.</p><button class="btn btn-primary btn-sm" onclick="runQualityScan()">Scan now</button></div>';
    }
}

var _scanPollTimer = null;
var _checkNames = {
    file_sizes: 'File Sizes', duplication: 'Duplicates (jscpd)',
    complexity: 'Complexity (radon)', css_quality: 'CSS Quality',
    js_quality: 'JS Duplicates', architecture: 'Architecture Rules',
    tests: 'Tests', done: 'Done'
};

function runQualityScan() {
    var body = document.getElementById('qualityBody');
    setQualityButtonState('running', 'Scanning');
    body.innerHTML = '<div id="scanProgress" style="padding:30px;text-align:center"><div class="spinner" style="margin:0 auto 12px"></div><div id="scanStep" style="font-size:13px;color:#888">Starting scan...</div><div id="scanBar" style="margin:16px auto;width:300px;height:6px;background:#222;border-radius:3px;overflow:hidden"><div id="scanFill" style="width:0%;height:100%;background:var(--accent);border-radius:3px;transition:width 0.3s"></div></div></div>';

    _scanPollTimer = setInterval(function() {
        api.get('/api/quality/progress/' + encodeURIComponent(PROJECT_NAME))
            .then(function(p) {
                if (!p || p.status === 'idle') return;
                var pct = p.total > 0 ? Math.round(p.step / p.total * 100) : 0;
                var el = document.getElementById('scanFill');
                if (el) el.style.width = pct + '%';
                var step = document.getElementById('scanStep');
                if (step) step.textContent = 'Check ' + p.step + '/' + p.total + ': ' + (_checkNames[p.check] || p.check);
                if (p.status === 'complete') clearInterval(_scanPollTimer);
            }).catch(function() {});
    }, 800);

    api.post('/api/quality/scan/' + encodeURIComponent(PROJECT_NAME))
        .then(function() { clearInterval(_scanPollTimer); qualityLoaded = false; loadQualityButtonState(); loadQualityTab(); })
        .catch(function(e) { clearInterval(_scanPollTimer); loadQualityButtonState(); body.innerHTML = '<div style="color:#f44336;padding:20px">Error: ' + e + '</div>'; });
}

function setProjectBaseline() {
    api.post('/api/quality/baseline/' + encodeURIComponent(PROJECT_NAME))
        .then(function(d) { alert('Baseline set: ' + d.score + ' (' + d.score_numeric + '/100)'); qualityLoaded = false; loadQualityButtonState(); loadQualityTab(); })
        .catch(function(e) { alert('Error: ' + e); });
}
