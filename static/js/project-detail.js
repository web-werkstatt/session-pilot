/**
 * Project Detail Page - Tabs, Plans, README, Sessions
 * Erwartet globale Variable: PROJECT_NAME (gesetzt im Template)
 */
let readmeFilename = 'README.md';
let easyMDE = null;
let plansLoaded = false;
let sessionsExtracted = false;
let qualityLoaded = false;

// === Tab Switching ===
function switchProjectTab(tab) {
    document.querySelectorAll('.project-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.project-tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('ptab_' + tab).classList.add('active');
    event.currentTarget.classList.add('active');

    if (tab === 'plans' && !plansLoaded) loadProjectPlans();
    if (tab === 'sessions' && !sessionsExtracted) extractSessions();
    if (tab === 'documents') loadDocuments();
    if (tab === 'quality' && !qualityLoaded) loadQualityTab();
}

// === Overview ===
async function loadProjectInfo() {
    try {
        const d = await api.get('/api/info?name=' + encodeURIComponent(PROJECT_NAME));

        const match = d.description.match(/<h3>Beschreibung<\/h3><p>(.*?)<\/p>/);
        document.getElementById('projectSubtitle').textContent = match ? match[1] : '';

        let sectionHtml = d.description
            .replace(/<h3>README<\/h3>[\s\S]*?(?=<h3>|<div class="export-hint"|$)/, '');

        // Sektionen in Bloecke wrappen fuer Grid-Layout
        sectionHtml = sectionHtml.replace(/<h3>/g, '</div><div class="info-block"><h3>');
        sectionHtml = sectionHtml.replace(/^<\/div>/, '');
        sectionHtml += '</div>';

        let html = '<div class="info-grid">' + sectionHtml + '</div>';

        // Platzhalter fuer teure Sections (werden async nachgeladen)
        html += '<div class="info-grid" id="slowSections"><div class="info-block"><div class="loading" style="padding:10px;font-size:12px;color:#555">Lade weitere Daten...</div></div></div>';

        html += `
        <h3>README</h3>
        <div class="readme-actions">
            <button class="btn-edit" onclick="toggleReadmeEdit()" id="readmeEditBtn"><i data-lucide="edit" class="icon"></i> Bearbeiten</button>
            <button class="btn-save" onclick="saveReadme()" id="readmeSaveBtn" style="display:none"><i data-lucide="save" class="icon"></i> Speichern</button>
            <button class="btn-cancel" onclick="cancelReadmeEdit()" id="readmeCancelBtn" style="display:none">Abbrechen</button>
            <span class="status" id="readmeStatus"></span>
        </div>
        <div id="readmeRendered" class="readme-rendered">Lade README...</div>
        <div id="readmeEditor"><textarea id="readmeTextarea"></textarea></div>`;

        document.getElementById('projectBody').innerHTML = html;
        if (typeof lucide !== 'undefined') lucide.createIcons();
        loadReadme();
        buildOverviewToc();

        // Teure Sections async nachladen
        loadSlowSections();
        // Quality-Score im Tab-Badge anzeigen
        api.get('/api/quality/report/' + encodeURIComponent(PROJECT_NAME))
            .then(function(d) { if (d.report) document.getElementById('qualityScore').textContent = d.report.score; })
            .catch(function() {});
    } catch(e) {
        document.getElementById('projectBody').innerHTML = '<div class="loading" style="color:#ff6666">Fehler: ' + e + '</div>';
    }
}

async function loadSlowSections() {
    try {
        const d = await api.get('/api/info/slow?name=' + encodeURIComponent(PROJECT_NAME));
        const el = document.getElementById('slowSections');
        if (!el) return;

        if (d.html) {
            // Sessions extrahieren fuer Tab
            const sessMatch = d.html.match(/<h3>Claude Sessions<\/h3>([\s\S]*?)(?=<h3>|$)/);
            if (sessMatch) {
                window._sessionsHtml = sessMatch[0];
                const linkCount = (sessMatch[1].match(/href=/g) || []).length;
                const countEl = document.getElementById('sessionsCount');
                if (linkCount > 0) countEl.textContent = linkCount;
            }
            let slowHtml = d.html.replace(/<h3>/g, '</div><div class="info-block"><h3>');
            slowHtml = slowHtml.replace(/^<\/div>/, '') + '</div>';
            el.innerHTML = slowHtml;
        } else {
            el.innerHTML = '';
        }
        if (typeof lucide !== 'undefined') lucide.createIcons();
        buildOverviewToc();
    } catch(e) {
        var el = document.getElementById('slowSections');
        if (el) el.innerHTML = '';
    }
}

function buildOverviewToc() {
    var toc = document.getElementById('overviewToc');
    if (!toc) return;
    var body = document.getElementById('projectBody');
    if (!body) return;
    // Nur direkte Sektions-h3, nicht aus README-Inhalt
    var headings = body.querySelectorAll('.info-block h3, #slowSections h3, #projectBody > h3');
    if (headings.length < 2) return;

    var html = '<div class="toc-title">Inhalt</div>';
    var idx = 0;
    headings.forEach(function(h) {
        if (h.closest('.readme-rendered')) return;
        var id = 'section-' + idx++;
        h.id = id;
        html += '<a href="#' + id + '" class="toc-link" onclick="document.getElementById(\'' + id + '\').scrollIntoView({behavior:\'smooth\',block:\'start\'});return false;">' + h.textContent + '</a>';
    });
    toc.innerHTML = html;
}

// === Quality Tab ===
async function loadQualityTab() {
    qualityLoaded = true;
    var body = document.getElementById('qualityBody');
    try {
        var d = await api.get('/api/quality/report/' + encodeURIComponent(PROJECT_NAME));
        var r = d.report;
        if (!r) {
            body.innerHTML = '<div style="text-align:center;padding:40px;color:#888"><p>Kein Quality-Report vorhanden.</p><button class="btn btn-primary btn-sm" onclick="runQualityScan()">Jetzt scannen</button></div>';
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
            if (d.diff.new_issues > 0) html += ' <span style="color:#f44336">+' + d.diff.new_issues + ' neu</span>';
            if (d.diff.fixed_issues > 0) html += ' <span style="color:#43a047">' + d.diff.fixed_issues + ' behoben</span>';
            html += '</div>';
        }

        html += '<div style="margin-left:auto;display:flex;gap:8px">';
        html += '<button class="btn btn-sm" onclick="runQualityScan()">Neu scannen</button>';
        html += '<button class="btn btn-sm" onclick="setProjectBaseline()">Baseline setzen</button>';
        html += '</div>';
        html += '</div>';

        // Issues nach Kategorie
        var categories = {};
        (r.issues || []).forEach(function(i) {
            if (i.status === 'ignored') return;
            if (!categories[i.category]) categories[i.category] = [];
            categories[i.category].push(i);
        });

        var catNames = { duplication: 'Duplikate', complexity: 'Komplexitaet', file_size: 'Dateigroessen', css_tokens: 'CSS-Qualitaet', css_undefined: 'CSS-Variablen', architecture: 'Architektur', test_failure: 'Tests', js_quality: 'JS-Qualitaet' };

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
        body.innerHTML = '<div style="text-align:center;padding:40px;color:#888"><p>Kein Quality-Report vorhanden.</p><button class="btn btn-primary btn-sm" onclick="runQualityScan()">Jetzt scannen</button></div>';
    }
}

var _scanPollTimer = null;
var _checkNames = {
    file_sizes: 'Dateigroessen', duplication: 'Duplikate (jscpd)',
    complexity: 'Komplexitaet (radon)', css_quality: 'CSS-Qualitaet',
    js_quality: 'JS-Duplikate', architecture: 'Architektur-Regeln',
    tests: 'Tests', done: 'Fertig'
};

function runQualityScan() {
    var body = document.getElementById('qualityBody');
    body.innerHTML = '<div id="scanProgress" style="padding:30px;text-align:center"><div class="spinner" style="margin:0 auto 12px"></div><div id="scanStep" style="font-size:13px;color:#888">Starte Scan...</div><div id="scanBar" style="margin:16px auto;width:300px;height:6px;background:#222;border-radius:3px;overflow:hidden"><div id="scanFill" style="width:0%;height:100%;background:var(--accent);border-radius:3px;transition:width 0.3s"></div></div></div>';

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
        .then(function() { clearInterval(_scanPollTimer); qualityLoaded = false; loadQualityTab(); })
        .catch(function(e) { clearInterval(_scanPollTimer); body.innerHTML = '<div style="color:#f44336;padding:20px">Fehler: ' + e + '</div>'; });
}

function setProjectBaseline() {
    api.post('/api/quality/baseline/' + encodeURIComponent(PROJECT_NAME))
        .then(function(d) { alert('Baseline gesetzt: ' + d.score + ' (' + d.score_numeric + '/100)'); qualityLoaded = false; loadQualityTab(); })
        .catch(function(e) { alert('Fehler: ' + e); });
}

// === Sessions Tab ===
function _outcomeBadge(outcome) {
    if (outcome === 'ok') return '<span class="outcome-badge outcome-ok">OK</span>';
    if (outcome === 'needs_fix') return '<span class="outcome-badge outcome-needs_fix">Fix</span>';
    if (outcome === 'reverted') return '<span class="outcome-badge outcome-reverted">Rev</span>';
    if (outcome === 'partial') return '<span class="outcome-badge outcome-partial">Teil</span>';
    return '';
}

async function extractSessions() {
    sessionsExtracted = true;
    var body = document.getElementById('sessionsBody');
    try {
        var d = await api.get('/api/sessions?project=' + encodeURIComponent(PROJECT_NAME) + '&limit=100');
        var sessions = d.sessions || [];
        if (!sessions.length) {
            body.innerHTML = '<p style="color:#888;padding:20px;text-align:center">Keine Claude Sessions fuer dieses Projekt</p>';
            return;
        }
        var countEl = document.getElementById('sessionsCount');
        if (countEl) countEl.textContent = sessions.length;

        var maxDur = Math.max(1, Math.max.apply(null, sessions.map(function(s) { return s.duration_ms || 0; })));

        var html = '<table class="data-table sessions-table"><thead><tr>';
        html += '<th>Account</th><th>Datum</th><th>Dauer</th><th>Msgs</th><th>Modell</th><th>Tokens</th><th>Branch</th><th>Status</th><th></th>';
        html += '</tr></thead><tbody>';

        sessions.forEach(function(s) {
            var date = s.started_at ? new Date(s.started_at) : null;
            var dateStr = date ? date.toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit',year:'2-digit'}) : '-';
            var timeStr = date ? date.toLocaleTimeString('de-DE', {hour:'2-digit',minute:'2-digit'}) : '';
            var acctClass = 'account-' + (s.account || '').replace(/[^a-z0-9]/g, '');
            var durPct = Math.min(100, ((s.duration_ms || 0) / maxDur) * 100);
            var model = (s.model || '-').replace('claude-', '').replace('opus-4-6', 'Opus').replace('sonnet-4-6', 'Sonnet');
            var msgs = (s.user_message_count || 0) + (s.assistant_message_count || 0);
            var branch = s.git_branch || '';

            html += '<tr class="row" style="cursor:pointer" onclick="location.href=\'/sessions/' + s.session_uuid + '\'">';
            html += '<td><span class="account-badge ' + acctClass + '">' + escapeHtml(s.account || '-') + '</span></td>';
            html += '<td><span style="color:#ccc">' + dateStr + '</span> <span style="color:#666;font-size:11px">' + timeStr + '</span></td>';
            html += '<td><div class="dur-wrap"><div class="dur-bar" style="width:' + durPct + '%"></div><span class="dur-text">' + (s.duration_formatted || '-') + '</span></div></td>';
            html += '<td>' + msgs + '</td>';
            html += '<td style="color:#888;font-size:12px">' + model + '</td>';
            html += '<td class="token-cell">' + (s.tokens_formatted || '-') + '</td>';
            html += '<td>' + (branch ? '<span class="branch" title="' + escapeHtml(branch) + '">' + escapeHtml(branch) + '</span>' : '') + '</td>';
            html += '<td>' + _outcomeBadge(s.outcome) + '</td>';
            html += '<td><div class="row-actions"><button class="row-action" onclick="event.stopPropagation();window.open(\'/api/sessions/' + s.session_uuid + '/export?format=json\')">JSON</button><button class="row-action" onclick="event.stopPropagation();window.open(\'/api/sessions/' + s.session_uuid + '/export?format=md\')">MD</button></div></td>';
            html += '</tr>';
        });

        html += '</tbody></table>';
        body.innerHTML = html;
    } catch(e) {
        body.innerHTML = '<p style="color:#f44336;padding:20px">Fehler: ' + e + '</p>';
    }
}

// === Plans Tab ===
async function loadProjectPlans() {
    plansLoaded = true;
    try {
        const variants = [
            PROJECT_NAME,
            PROJECT_NAME.replace(/-/g, '_'),
            PROJECT_NAME.replace(/_/g, '-'),
        ];
        let allPlans = [];
        for (const v of variants) {
            const d = await api.get('/api/plans?project=' + encodeURIComponent(v));
            if (d.plans && d.plans.length > 0) allPlans = allPlans.concat(d.plans);
        }
        const seen = new Set();
        allPlans = allPlans.filter(p => { if (seen.has(p.id)) return false; seen.add(p.id); return true; });

        const countEl = document.getElementById('plansCount');
        if (allPlans.length > 0) countEl.textContent = allPlans.length;

        if (allPlans.length === 0) {
            document.getElementById('plansBody').innerHTML = `
                <div style="text-align:center;padding:40px;color:#888">
                    <p>Keine Plans fuer dieses Projekt</p>
                    <a href="/plans" style="color:#0078d4">Alle Plans anzeigen</a>
                </div>`;
            return;
        }

        const statusColors = {
            draft: { bg: 'transparent', border: '#666', label: 'Entwurf' },
            active: { bg: 'rgba(0,120,212,0.12)', border: '#0078d4', label: 'Aktiv' },
            completed: { bg: 'rgba(46,204,113,0.10)', border: '#2ecc71', label: 'Erledigt' },
            archived: { bg: 'rgba(80,80,80,0.15)', border: '#555', label: 'Archiv' },
        };

        let html = '<div class="plans-cards">';
        allPlans.forEach(p => {
            const sc = statusColors[p.status] || statusColors.draft;
            const date = p.created_at ? new Date(p.created_at).toLocaleDateString('de-DE') : '';
            const hasSession = p.session_slug && p.session_slug !== 'None';
            const sessionLink = hasSession
                ? `<span class="badge" style="font-size:10px;background:rgba(0,120,212,0.2);color:#4fc3f7">Session</span>`
                : '';
            const context = p.context_summary
                ? `<div class="plan-mini-context">${p.context_summary.substring(0, 120)}${p.context_summary.length > 120 ? '...' : ''}</div>`
                : '';
            html += `
            <div class="plan-mini-card" style="background:${sc.bg}; border-left:3px solid ${sc.border}" onclick="location.href='/plans?plan=${p.id}'">
                <div class="plan-mini-top">
                    <span class="badge badge-status badge-${p.status}" style="font-size:11px">${sc.label}</span>
                    <span style="font-size:11px;color:#888">${date}</span>
                </div>
                <div class="plan-mini-title">${p.title}</div>
                ${context}
                <div class="plan-mini-footer">
                    <span class="badge badge-cat" style="font-size:10px">${p.category || 'plan'}</span>
                    ${sessionLink}
                </div>
            </div>`;
        });
        html += `</div><div style="text-align:right;margin-top:12px"><a href="/plans?project=${encodeURIComponent(PROJECT_NAME)}" style="color:#0078d4;font-size:13px">Alle Plans anzeigen &rarr;</a></div>`;
        document.getElementById('plansBody').innerHTML = html;
    } catch(e) {
        document.getElementById('plansBody').innerHTML = '<p style="color:#ff6666;padding:20px">Fehler: ' + e + '</p>';
    }
}

// === README ===
async function loadReadme() {
    try {
        const d = await api.get('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/readme');
        readmeFilename = d.filename || 'README.md';
        if (d.html) {
            document.getElementById('readmeRendered').innerHTML = d.html;
        } else {
            document.getElementById('readmeRendered').innerHTML = '<p style="color:#666;font-style:italic">Keine README.md vorhanden</p>';
        }
        document.getElementById('readmeTextarea').value = d.raw || '';
    } catch(e) {
        document.getElementById('readmeRendered').innerHTML = '<p style="color:#ff6666">Fehler: ' + e + '</p>';
    }
}

function toggleReadmeEdit() {
    document.getElementById('readmeRendered').style.display = 'none';
    document.getElementById('readmeEditor').style.display = 'block';
    document.getElementById('readmeEditBtn').style.display = 'none';
    document.getElementById('readmeSaveBtn').style.display = 'inline-block';
    document.getElementById('readmeCancelBtn').style.display = 'inline-block';
    if (!easyMDE) {
        easyMDE = new EasyMDE({
            element: document.getElementById('readmeTextarea'),
            spellChecker: false, autofocus: true, minHeight: '400px',
            status: ['lines', 'words'],
            toolbar: ['bold','italic','heading','|','code','quote','unordered-list','ordered-list','|','link','image','table','horizontal-rule','|','preview','side-by-side','fullscreen','|','guide'],
            previewRender: function(plainText) { return this.parent.markdown(plainText); }
        });
    }
}

function cancelReadmeEdit() {
    document.getElementById('readmeRendered').style.display = 'block';
    document.getElementById('readmeEditor').style.display = 'none';
    document.getElementById('readmeEditBtn').style.display = 'inline-block';
    document.getElementById('readmeSaveBtn').style.display = 'none';
    document.getElementById('readmeCancelBtn').style.display = 'none';
    document.getElementById('readmeStatus').textContent = '';
    if (easyMDE) loadReadme();
}

async function saveReadme() {
    const content = easyMDE ? easyMDE.value() : document.getElementById('readmeTextarea').value;
    const status = document.getElementById('readmeStatus');
    status.textContent = 'Speichern...'; status.style.color = '#888';
    try {
        const d = await api.put('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/readme', {content, filename: readmeFilename});
        if (d.success) { status.textContent = 'Gespeichert'; status.style.color = '#4caf50'; await loadReadme(); cancelReadmeEdit(); }
        else { status.textContent = d.error; status.style.color = '#ff4444'; }
    } catch(e) { status.textContent = 'Fehler: ' + e; status.style.color = '#ff4444'; }
}

function exportProject(fmt) {
    window.open('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/export?format=' + fmt, '_blank');
}

// === Init ===
loadProjectInfo();
initGitPanel(PROJECT_NAME);
