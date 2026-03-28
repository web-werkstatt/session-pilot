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
