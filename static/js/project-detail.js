/**
 * Project Detail Page - Tabs, Plans, README, Sessions
 * Erwartet globale Variable: PROJECT_NAME (gesetzt im Template)
 */
let readmeFilename = 'README.md';
let easyMDE = null;
let plansLoaded = false;
let sessionsExtracted = false;

// === Tab Switching ===
function switchProjectTab(tab) {
    document.querySelectorAll('.project-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.project-tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById('ptab_' + tab).classList.add('active');
    event.currentTarget.classList.add('active');

    if (tab === 'plans' && !plansLoaded) loadProjectPlans();
    if (tab === 'sessions' && !sessionsExtracted) extractSessions();
    if (tab === 'documents') loadDocuments();
}

// === Overview ===
async function loadProjectInfo() {
    try {
        const r = await fetch('/api/info?name=' + encodeURIComponent(PROJECT_NAME));
        const d = await r.json();

        const match = d.description.match(/<h3>Beschreibung<\/h3><p>(.*?)<\/p>/);
        document.getElementById('projectSubtitle').textContent = match ? match[1] : '';

        let html = d.description
            .replace(/<h3>README<\/h3>[\s\S]*?(?=<h3>|<div class="export-hint"|$)/, '')
            .replace(/<h3>Claude Sessions<\/h3>[\s\S]*?(?=<h3>|<div class="export-hint"|$)/, '');

        const sessMatch = d.description.match(/<h3>Claude Sessions<\/h3>([\s\S]*?)(?=<h3>|<div class="export-hint"|$)/);
        if (sessMatch) {
            window._sessionsHtml = sessMatch[0];
            const linkCount = (sessMatch[1].match(/href=/g) || []).length;
            const countEl = document.getElementById('sessionsCount');
            if (linkCount > 0) countEl.textContent = linkCount;
        }

        html += `
        <h3>README</h3>
        <div class="readme-actions">
            <button class="btn-edit" onclick="toggleReadmeEdit()" id="readmeEditBtn">✏️ Bearbeiten</button>
            <button class="btn-save" onclick="saveReadme()" id="readmeSaveBtn" style="display:none">💾 Speichern</button>
            <button class="btn-cancel" onclick="cancelReadmeEdit()" id="readmeCancelBtn" style="display:none">Abbrechen</button>
            <span class="status" id="readmeStatus"></span>
        </div>
        <div id="readmeRendered" class="readme-rendered">Lade README...</div>
        <div id="readmeEditor"><textarea id="readmeTextarea"></textarea></div>`;

        document.getElementById('projectBody').innerHTML = html;
        loadReadme();
    } catch(e) {
        document.getElementById('projectBody').innerHTML = '<div class="loading" style="color:#ff6666">Fehler: ' + e + '</div>';
    }
}

// === Sessions Tab ===
function extractSessions() {
    sessionsExtracted = true;
    if (window._sessionsHtml) {
        document.getElementById('sessionsBody').innerHTML = window._sessionsHtml;
    } else {
        document.getElementById('sessionsBody').innerHTML = '<p style="color:#888;padding:20px">Keine Claude Sessions fuer dieses Projekt</p>';
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
            const r = await fetch('/api/plans?project=' + encodeURIComponent(v));
            const d = await r.json();
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
            const sessionLink = p.session_slug
                ? `<a href="/sessions/${p.session_slug}" style="color:#0078d4;font-size:12px;text-decoration:none">Session</a>`
                : '';
            const context = p.context_summary
                ? `<div class="plan-mini-context">${p.context_summary.substring(0, 120)}${p.context_summary.length > 120 ? '...' : ''}</div>`
                : '';
            html += `
            <a href="/plans" class="plan-mini-card" style="background:${sc.bg}; border-left:3px solid ${sc.border}">
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
            </a>`;
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
        const r = await fetch('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/readme');
        const d = await r.json();
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
        const r = await fetch('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/readme', {
            method: 'PUT', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content, filename: readmeFilename})
        });
        const d = await r.json();
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

// Plans-Count vorladen
(async () => {
    const variants = [PROJECT_NAME, PROJECT_NAME.replace(/-/g,'_'), PROJECT_NAME.replace(/_/g,'-')];
    let total = 0;
    for (const v of variants) {
        try {
            const r = await fetch('/api/plans?project=' + encodeURIComponent(v));
            const d = await r.json();
            total += (d.plans || []).length;
        } catch(e) {}
    }
    if (total > 0) document.getElementById('plansCount').textContent = total;
})();
