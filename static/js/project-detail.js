/**
 * Project Detail Page - Details, Planning, README, Session History
 * Erwartet globale Variable: PROJECT_NAME (gesetzt im Template)
 */
let readmeFilename = 'README.md';
let easyMDE = null;
let plansLoaded = false;
let workflowLoaded = false;
let sessionsExtracted = false;
let qualityLoaded = false;
let qualityStatusLoaded = false;
let dispatchLoaded = false;
// === Tab Switching ===
function switchProjectTab(tab, trigger) {
    document.querySelectorAll('.project-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.project-tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('ptab_' + tab).classList.add('active');
    if (trigger) trigger.classList.add('active');

    if (tab === 'plans' && !plansLoaded) loadProjectPlans();
    if (tab === 'workflow' && !workflowLoaded) loadWorkflowTab();
    if (tab === 'sessions' && !sessionsExtracted) extractSessions();
    if (tab === 'documents') loadDocuments();
    if (tab === 'quality' && !qualityLoaded) loadQualityTab();
    if (tab === 'heatmap') loadFileHeatmap();
    if (tab === 'governance' && !governanceTabLoaded) loadGovernanceTab();
    if (tab === 'dispatch' && !dispatchLoaded) { dispatchLoaded = true; Dispatch.load(); }
}

function switchProjectTabByName(tab) {
    var target = document.getElementById('ptab_' + tab);
    if (!target) return;
    var button = document.querySelector(".project-tab[onclick*=\"'" + tab + "'\"]");
    switchProjectTab(tab, button || null);
}

function normalizeProjectTabName(tab) {
    var value = String(tab || '').toLowerCase();
    if (value === 'details') return 'overview';
    if (value === 'planning') return 'plans';
    return value;
}

function initProjectTabFromQuery() {
    var params = new URLSearchParams(window.location.search);
    var tab = normalizeProjectTabName(params.get('tab'));
    if (!tab) return;
    switchProjectTabByName(tab);
}

function projectDetailGoBack() {
    var params = new URLSearchParams(window.location.search);
    var returnTo = params.get('return_to') || '';
    if (returnTo) {
        window.location.href = returnTo;
        return;
    }
    if (document.referrer) {
        try {
            var refUrl = new URL(document.referrer, window.location.origin);
            if (refUrl.origin === window.location.origin && refUrl.pathname !== window.location.pathname) {
                window.history.back();
                return;
            }
        } catch (e) {
        }
    }
    window.location.href = '/';
}

function loadWorkflowTab() {
    workflowLoaded = true;
    loadWorkflowLoop();
}

function loadData() {
    loadProjectInfo();
    if (typeof loadGroups === 'function') loadGroups();
}

function setQualityButtonState(state, label) {
    var button = document.getElementById('qualitySecondaryLink');
    var badge = document.getElementById('qualityScore');
    if (!button || !badge) return;
    button.classList.remove('quality-state-none', 'quality-state-good', 'quality-state-warning', 'quality-state-critical', 'quality-state-running');
    if (state) button.classList.add('quality-state-' + state);
    if (label) badge.textContent = label;
}

function getQualityStateFromReport(report) {
    if (!report) return { state: 'none', label: 'No Scan' };
    var score = Number(report.score_numeric);
    if (!isNaN(score)) {
        if (score < 40) return { state: 'critical', label: report.score || String(score) };
        if (score < 60) return { state: 'warning', label: report.score || String(score) };
    }
    return { state: 'good', label: report.score || 'OK' };
}

function loadQualityButtonState() {
    qualityStatusLoaded = true;
    api.get('/api/quality/report/' + encodeURIComponent(PROJECT_NAME))
        .then(function(d) {
            var next = getQualityStateFromReport(d && d.report ? d.report : null);
            setQualityButtonState(next.state, next.label);
        })
        .catch(function() {
            setQualityButtonState('none', 'No Scan');
        });
}

function normalizeProjectSubtitle(text) {
    return String(text || '')
        .replace(/&lt;br\s*\/?&gt;?/gi, ' ')
        .replace(/<br\s*\/?>/gi, ' ')
        .replace(/<br$/i, '')
        .replace(/\s+/g, ' ')
        .trim();
}

// === Details ===
async function loadProjectInfo() {
    try {
        const d = await api.get('/api/info?name=' + encodeURIComponent(PROJECT_NAME));
        const hasReadmeSection = /<h3>README<\/h3>/.test(d.description);

        const match = d.description.match(/<h3>(?:Beschreibung|Description)<\/h3><p>(.*?)<\/p>/);
        document.getElementById('projectSubtitle').textContent = normalizeProjectSubtitle(match ? match[1] : '');

        let sectionHtml = d.description
            .replace(/<h3>README<\/h3>[\s\S]*?(?=<h3>|<div class="export-hint"|$)/, '');

        // Sektionen in Bloecke wrappen fuer Grid-Layout
        sectionHtml = sectionHtml.replace(/<h3>/g, '</div><div class="info-block"><h3>');
        sectionHtml = sectionHtml.replace(/^<\/div>/, '');
        sectionHtml += '</div>';

        let html = '<div class="info-grid">' + sectionHtml + '</div>';

        // Platzhalter fuer teure Sections (werden async nachgeladen)
        html += '<div class="info-grid" id="slowSections"><div class="info-block"><div class="loading" style="padding:10px;font-size:12px;color:#555">Loading additional data...</div></div></div>';

        if (hasReadmeSection) {
            html += `
            <h3>README</h3>
            <div class="readme-actions">
                <button class="btn-edit" onclick="toggleReadmeEdit()" id="readmeEditBtn"><i data-lucide="edit" class="icon"></i> Edit</button>
                <button class="btn-save" onclick="saveReadme()" id="readmeSaveBtn" style="display:none"><i data-lucide="save" class="icon"></i> Save</button>
                <button class="btn-cancel" onclick="cancelReadmeEdit()" id="readmeCancelBtn" style="display:none">Cancel</button>
                <span class="status" id="readmeStatus"></span>
            </div>
            <div id="readmeRendered" class="readme-rendered">Loading README...</div>
            <div id="readmeEditor"><textarea id="readmeTextarea"></textarea></div>`;
        }

        document.getElementById('projectBody').innerHTML = html;
        if (typeof lucide !== 'undefined') lucide.createIcons();
        if (hasReadmeSection) loadReadme();
        buildOverviewToc();

        // Teure Sections async nachladen
        loadSlowSections();
        if (!qualityStatusLoaded) loadQualityButtonState();
    } catch(e) {
        document.getElementById('projectBody').innerHTML = '<div class="loading" style="color:#ff6666">Error: ' + e + '</div>';
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
    var headings = body.querySelectorAll('.info-block h3, #slowSections h3, #projectBody > h3');
    if (headings.length < 2) return;

    var html = '<div class="toc-title">Contents</div>';
    var idx = 0;
    headings.forEach(function(h) {
        if (h.closest('.readme-rendered')) return;
        var id = 'section-' + idx++;
        h.id = id;
        html += '<a href="#' + id + '" class="toc-link" onclick="document.getElementById(\'' + id + '\').scrollIntoView({behavior:\'smooth\',block:\'start\'});return false;">' + h.textContent + '</a>';
    });
    toc.innerHTML = html;
}

// === Session History Tab ===
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
        var d = await api.get('/api/sessions?project=' + encodeURIComponent(PROJECT_NAME) + '&limit=20');
        var sessions = d.sessions || [];
        if (!sessions.length) {
            body.innerHTML = '<p style="color:#888;padding:20px;text-align:center">No sessions linked to this project yet.</p>';
            return;
        }
        var countEl = document.getElementById('sessionsCount');
        if (countEl) countEl.textContent = sessions.length;

        // Aggregate stats
        var accountCounts = {};
        var totalDuration = 0;
        var totalTokens = 0;
        sessions.forEach(function(s) {
            var acct = s.account || 'unknown';
            accountCounts[acct] = (accountCounts[acct] || 0) + 1;
            totalDuration += s.duration_ms || 0;
            totalTokens += (s.total_input_tokens || s.input_tokens || 0) + (s.total_output_tokens || s.output_tokens || 0);
        });

        var html = '<div class="activity-summary-header">'
            + '<h3 class="activity-summary-title">Activity Overview</h3>'
            + '<a class="activity-summary-viewall" href="/sessions?project=' + encodeURIComponent(PROJECT_NAME) + '">View all sessions &rarr;</a>'
            + '</div>';

        // Stats row
        html += '<div class="activity-stats-row">';
        html += '<div class="activity-stat"><span class="activity-stat-value">' + sessions.length + '</span><span class="activity-stat-label">Sessions</span></div>';
        var durationHrs = Math.round(totalDuration / 3600000 * 10) / 10;
        html += '<div class="activity-stat"><span class="activity-stat-value">' + (durationHrs >= 1 ? durationHrs + 'h' : Math.round(totalDuration / 60000) + 'm') + '</span><span class="activity-stat-label">Total Time</span></div>';
        var tokensFmt = totalTokens >= 1000000 ? (totalTokens / 1000000).toFixed(1) + 'M' : totalTokens >= 1000 ? Math.round(totalTokens / 1000) + 'K' : String(totalTokens);
        html += '<div class="activity-stat"><span class="activity-stat-value">' + tokensFmt + '</span><span class="activity-stat-label">Tokens</span></div>';
        html += '<div class="activity-stat"><span class="activity-stat-value">' + Object.keys(accountCounts).length + '</span><span class="activity-stat-label">Tools</span></div>';
        html += '</div>';

        // Account breakdown
        html += '<div class="activity-accounts">';
        Object.keys(accountCounts).sort(function(a,b) { return accountCounts[b] - accountCounts[a]; }).forEach(function(acct) {
            var cls = 'account-' + acct.replace(/[^a-z0-9]/g, '');
            var acctStyle = typeof getAccountBadgeStyle === 'function' ? getAccountBadgeStyle(acct, '') : '';
            html += '<span class="account-badge ' + cls + '" style="' + escapeHtml(acctStyle) + '">' + escapeHtml(acct) + ' (' + accountCounts[acct] + ')</span> ';
        });
        html += '</div>';

        // Recent sessions compact list
        html += '<h4 class="activity-recent-title">Recent Sessions</h4>';
        html += '<div class="activity-recent-list">';
        sessions.slice(0, 10).forEach(function(s) {
            var date = s.started_at ? new Date(s.started_at) : null;
            var dateStr = date ? date.toLocaleDateString('en-US', {month:'short',day:'numeric'}) : '-';
            var timeStr = date ? date.toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit'}) : '';
            var acctClass = 'account-' + (s.account || '').replace(/[^a-z0-9]/g, '');
            var acctStyle = typeof getAccountBadgeStyle === 'function' ? getAccountBadgeStyle(s.account, s.tool) : '';
            var model = (s.model || '-').replace('claude-', '').replace('opus-4-6', 'Opus').replace('sonnet-4-6', 'Sonnet');

            html += '<a class="activity-recent-item" href="/sessions/' + encodeURIComponent(s.session_uuid) + '">';
            html += '<span class="account-badge ' + acctClass + '" style="' + escapeHtml(acctStyle) + '">' + escapeHtml(s.account || '-') + '</span>';
            html += '<span class="activity-recent-date">' + dateStr + ' ' + timeStr + '</span>';
            html += '<span class="activity-recent-meta">' + escapeHtml(model) + '</span>';
            html += '<span class="activity-recent-meta">' + escapeHtml(s.duration_formatted || '-') + '</span>';
            html += _outcomeBadge(s.outcome);
            html += '</a>';
        });
        html += '</div>';

        body.innerHTML = html;
    } catch(e) {
        body.innerHTML = '<p style="color:#f44336;padding:20px">Error: ' + e + '</p>';
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
            document.getElementById('readmeRendered').innerHTML = '<p style="color:#666;font-style:italic">No README.md found</p>';
        }
        document.getElementById('readmeTextarea').value = d.raw || '';
    } catch(e) {
        document.getElementById('readmeRendered').innerHTML = '<p style="color:#ff6666">Error: ' + e + '</p>';
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
    status.textContent = 'Saving...'; status.style.color = '#888';
    try {
        const d = await api.put('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/readme', {content, filename: readmeFilename});
        if (d.success) { status.textContent = 'Saved'; status.style.color = '#4caf50'; await loadReadme(); cancelReadmeEdit(); }
        else { status.textContent = d.error; status.style.color = '#ff4444'; }
    } catch(e) { status.textContent = 'Error: ' + e; status.style.color = '#ff4444'; }
}

function exportProject(fmt) {
    window.open('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/export?format=' + fmt, '_blank');
}

// === Model Recommendation Badge ===
async function loadModelRecommendation() {
    try {
        const data = await api.get('/api/analytics/model-recommendation?project=' + encodeURIComponent(PROJECT_NAME));
        const el = document.getElementById('modelRecommendationBadge');
        if (data.recommended && el) {
            el.className = 'model-recommendation';
            el.textContent = 'Recommended: ' + data.recommended;
        }
    } catch (e) { /* ignore */ }
}

// === Init ===
if (typeof setActiveProjectContext === 'function') {
    setActiveProjectContext(PROJECT_NAME);
}
if (typeof loadGroups === 'function') {
    loadGroups();
}
loadProjectInfo();
if (typeof preloadProjectPlansCount === 'function') {
    preloadProjectPlansCount();
}
initProjectTabFromQuery();
initGitPanel(PROJECT_NAME);
loadModelRecommendation();
if (typeof loadRiskRadarPanel === 'function') {
    loadRiskRadarPanel();
}
