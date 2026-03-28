/* Scaffold Wizard */

let currentStep = 1;
let templates = [];
let selectedTemplate = 'blank';

// === Step Navigation ===
function goStep(step) {
    if (step === 2 && !document.getElementById('projName').value) return;

    document.querySelectorAll('.wizard-panel').forEach(p => p.style.display = 'none');
    document.getElementById('step' + step).style.display = '';

    document.querySelectorAll('.wizard-step').forEach(s => {
        const sn = parseInt(s.dataset.step);
        s.classList.remove('active', 'done');
        if (sn === step) s.classList.add('active');
        else if (sn < step) s.classList.add('done');
    });

    currentStep = step;
    if (step === 2) loadTemplates();
    if (step === 4) loadPreview();
}

// === Step 1: Name Validation ===
function validateName() {
    const input = document.getElementById('projName');
    const hint = document.getElementById('nameHint');
    const btn = document.getElementById('btnNext1');
    const name = input.value;

    if (!name) {
        input.className = '';
        hint.textContent = 'Kleinbuchstaben, Zahlen, Bindestriche';
        hint.className = 'sc-hint';
        btn.disabled = true;
        return;
    }

    if (!/^[a-z][a-z0-9_-]*$/.test(name)) {
        input.className = 'invalid';
        hint.textContent = 'Nur Kleinbuchstaben, Zahlen, - und _ (muss mit Buchstabe beginnen)';
        hint.className = 'sc-hint error';
        btn.disabled = true;
        return;
    }

    input.className = 'valid';
    hint.textContent = 'Projektpfad: /mnt/projects/' + name;
    hint.className = 'sc-hint';
    btn.disabled = false;
}

// === Step 2: Templates ===
async function loadTemplates() {
    if (templates.length) { renderTemplates(); return; }
    try {
        templates = await api.get('/api/scaffold/templates');
        renderTemplates();
    } catch(e) { console.error(e); }
}

function renderTemplates() {
    const grid = document.getElementById('templateGrid');
    grid.innerHTML = templates.map(t => {
        const sel = t.id === selectedTemplate ? 'selected' : '';
        const files = t.files.slice(0, 5).join(', ');
        return `<div class="sc-tmpl-card ${sel}" onclick="selectTemplate('${t.id}')">
            <div class="sc-tmpl-name">${t.name}</div>
            <div class="sc-tmpl-desc">${t.description}</div>
            <div class="sc-tmpl-files">${files}${t.files.length > 5 ? ' ...' : ''}</div>
        </div>`;
    }).join('');
}

function selectTemplate(id) {
    selectedTemplate = id;
    renderTemplates();
}

// === Step 4: Preview ===
function getConfig() {
    const aiTools = [];
    if (document.getElementById('aiClaude').checked) aiTools.push('claude');
    if (document.getElementById('aiCodex').checked) aiTools.push('codex');
    if (document.getElementById('aiGemini').checked) aiTools.push('gemini');

    return {
        name: document.getElementById('projName').value,
        description: document.getElementById('projDesc').value,
        type: document.getElementById('projType').value,
        group: document.getElementById('projGroup').value,
        template: selectedTemplate,
        ai_tools: aiTools,
        docker: document.getElementById('optDocker').checked,
        git_init: document.getElementById('optGit').checked,
        gitea_create: document.getElementById('optGitea').checked,
    };
}

async function loadPreview() {
    const config = getConfig();
    document.getElementById('previewName').textContent = config.name;
    document.getElementById('previewType').textContent = config.type;
    document.getElementById('previewDesc').textContent = config.description || 'Keine Beschreibung';

    try {
        const d = await api.post('/api/scaffold/preview', config);
        if (d.error) {
            document.getElementById('previewFiles').innerHTML = `<span style="color:#ef5350">${d.error}</span>`;
            document.getElementById('btnCreate').disabled = true;
            return;
        }
        document.getElementById('previewFiles').innerHTML = d.files.map(f => {
            const icon = f.endsWith('/') ? '&#128193;' : '&#128196;';
            return `<div><span class="file-icon">${icon}</span>${f}</div>`;
        }).join('');
        document.getElementById('btnCreate').disabled = false;
    } catch(e) {
        document.getElementById('previewFiles').innerHTML = '<span style="color:#ef5350">Fehler beim Laden der Vorschau</span>';
    }
}

// === Create ===
async function createProject() {
    const btn = document.getElementById('btnCreate');
    btn.disabled = true;
    btn.textContent = 'Erstelle...';

    try {
        const d = await api.post('/api/scaffold/create', getConfig());

        document.querySelectorAll('.wizard-panel').forEach(p => p.style.display = 'none');
        document.getElementById('stepResult').style.display = '';
        document.querySelectorAll('.wizard-step').forEach(s => s.classList.add('done'));

        if (d.success) {
            const logHtml = d.log.map(l => `<div>${l}</div>`).join('');
            document.getElementById('resultContent').innerHTML = `
                <div class="sc-result-icon">&#10003;</div>
                <h2>Projekt "${d.name}" erstellt!</h2>
                <div class="sc-result-log">${logHtml}</div>
                <div class="sc-result-actions">
                    <a href="/project/${d.name}" class="sc-btn sc-btn-primary">Projekt oeffnen</a>
                    <a href="/" class="sc-btn">Dashboard</a>
                </div>`;
        } else {
            document.getElementById('resultContent').innerHTML = `
                <div class="sc-result-icon" style="color:#ef5350">&#10007;</div>
                <h2 style="color:#ef5350">Fehler</h2>
                <p style="color:#aaa">${d.error}</p>
                <div class="sc-result-actions">
                    <button class="sc-btn" onclick="goStep(1)">Zurueck</button>
                </div>`;
        }
    } catch(e) {
        btn.disabled = false;
        btn.textContent = 'Projekt erstellen';
        console.error(e);
    }
}

// Init
validateName();
