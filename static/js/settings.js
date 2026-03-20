/* Settings Page */

let pricingData = [];
let currentProvider = 'all';

// === Tab Navigation ===
function switchTab(tab, btn) {
    document.querySelectorAll('.settings-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('section-' + tab).style.display = '';
    btn.classList.add('active');

    if (tab === 'pricing' && !pricingData.length) loadPricing();
    if (tab === 'accounts') loadAccounts();
    if (tab === 'system') loadSystem();
}

// === Pricing ===
async function loadPricing() {
    try {
        const r = await fetch('/api/settings/pricing');
        if (!r.ok) return;
        pricingData = await r.json();
        renderPricing();
    } catch(e) { console.error(e); }
}

function filterProvider(provider, btn) {
    currentProvider = provider;
    document.querySelectorAll('.s-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderPricing();
}

function providerBadge(p) {
    if (!p) return '';
    return `<span class="s-provider s-provider-${p}">${p}</span>`;
}

function renderPricing() {
    const tbody = document.getElementById('pricingBody');
    const filtered = currentProvider === 'all'
        ? pricingData
        : pricingData.filter(p => p.provider === currentProvider);

    if (!filtered.length) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#666;padding:20px">Keine Modelle</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(p => `<tr data-id="${p.id}">
        <td><input type="text" value="${esc(p.model_pattern)}" data-field="model_pattern"></td>
        <td><input type="text" value="${esc(p.display_name || '')}" data-field="display_name"></td>
        <td><input type="text" value="${esc(p.provider || '')}" data-field="provider" class="input-sm"></td>
        <td><input type="number" step="0.01" value="${p.input_price}" data-field="input_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="${p.output_price}" data-field="output_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="${p.cache_read_factor}" data-field="cache_read_factor" class="input-xs"></td>
        <td><input type="number" step="0.01" value="${p.cache_create_factor}" data-field="cache_create_factor" class="input-xs"></td>
        <td class="s-btn-group">
            <button class="s-btn s-btn-sm s-btn-save" onclick="savePricing(this)">&#10003;</button>
            <button class="s-btn s-btn-sm s-btn-del" onclick="deletePricing(${p.id})">&#10005;</button>
        </td>
    </tr>`).join('');
}

function esc(s) { return (s || '').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

function addPricingRow() {
    const tbody = document.getElementById('pricingBody');
    const tr = document.createElement('tr');
    tr.dataset.id = '';
    tr.innerHTML = `
        <td><input type="text" data-field="model_pattern" placeholder="z.B. gpt-6"></td>
        <td><input type="text" data-field="display_name" placeholder="GPT-6"></td>
        <td><input type="text" data-field="provider" placeholder="openai" class="input-sm"></td>
        <td><input type="number" step="0.01" value="3.00" data-field="input_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="15.00" data-field="output_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="0.10" data-field="cache_read_factor" class="input-xs"></td>
        <td><input type="number" step="0.01" value="1.25" data-field="cache_create_factor" class="input-xs"></td>
        <td class="s-btn-group">
            <button class="s-btn s-btn-sm s-btn-save" onclick="savePricing(this)">&#10003;</button>
            <button class="s-btn s-btn-sm s-btn-del" onclick="this.closest('tr').remove()">&#10005;</button>
        </td>`;
    tbody.prepend(tr);
    tr.querySelector('input').focus();
}

async function savePricing(btn) {
    const tr = btn.closest('tr');
    const data = {id: tr.dataset.id ? parseInt(tr.dataset.id) : null};
    tr.querySelectorAll('input').forEach(inp => {
        data[inp.dataset.field] = inp.type === 'number' ? parseFloat(inp.value) : inp.value;
    });
    if (!data.model_pattern) return;

    try {
        const r = await fetch('/api/settings/pricing', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        if (r.ok) {
            btn.textContent = '\u2713';
            btn.style.background = '#4caf50';
            setTimeout(() => { btn.style.background = ''; loadPricing(); }, 600);
        }
    } catch(e) { console.error(e); }
}

async function deletePricing(id) {
    if (!confirm('Modell-Preis loeschen?')) return;
    try {
        await fetch('/api/settings/pricing/' + id, {method: 'DELETE'});
        loadPricing();
    } catch(e) { console.error(e); }
}

// === Accounts ===
async function loadAccounts() {
    try {
        const r = await fetch('/api/settings/accounts');
        if (!r.ok) return;
        const data = await r.json();

        document.getElementById('accountCards').innerHTML = data.map(a => {
            const toolClass = 's-tool-' + a.tool;
            const lastSession = a.last_session
                ? new Date(a.last_session).toLocaleDateString('de-DE', {day:'2-digit',month:'2-digit',year:'numeric'})
                : 'Nie';
            return `<div class="s-card">
                <div class="s-card-header">
                    <span class="s-card-name">${esc(a.name)}</span>
                    <span class="s-card-tool ${toolClass}">${a.tool}</span>
                </div>
                <div class="s-card-detail">${esc(a.config_dir)}</div>
                <div class="s-card-stat">
                    <div class="s-card-stat-item">
                        <div class="s-card-stat-value">${a.sessions}</div>
                        <div class="s-card-stat-label">Sessions</div>
                    </div>
                    <div class="s-card-stat-item">
                        <div class="s-card-stat-value">${lastSession}</div>
                        <div class="s-card-stat-label">Letzte Session</div>
                    </div>
                </div>
            </div>`;
        }).join('');

        if (!data.length) {
            document.getElementById('accountCards').innerHTML = '<div style="color:#666">Keine AI-Accounts erkannt.</div>';
        }
    } catch(e) { console.error(e); }
}

// === System ===
async function loadSystem() {
    try {
        const r = await fetch('/api/settings/system');
        if (!r.ok) return;
        const d = await r.json();

        document.getElementById('systemInfo').innerHTML = `
            <div class="s-info-group">
                <h3>Server</h3>
                <div class="s-info-row"><span class="s-info-label">Host</span><span class="s-info-value">${d.host}:${d.port}</span></div>
                <div class="s-info-row"><span class="s-info-label">Projekte-Pfad</span><span class="s-info-value">${esc(d.projects_dir)}</span></div>
                <div class="s-info-row"><span class="s-info-label">Gitea</span><span class="s-info-value">${esc(d.gitea_url)}</span></div>
                <div class="s-info-row"><span class="s-info-label">Gitea User</span><span class="s-info-value">${esc(d.gitea_user)}</span></div>
            </div>
            <div class="s-info-group">
                <h3>Datenbank</h3>
                <div class="s-info-row"><span class="s-info-label">Host</span><span class="s-info-value">${d.db_host}:${d.db_port}</span></div>
                <div class="s-info-row"><span class="s-info-label">Name</span><span class="s-info-value">${esc(d.db_name)}</span></div>
                <div class="s-info-row"><span class="s-info-label">Groesse</span><span class="s-info-value">${d.db_size}</span></div>
            </div>
            <div class="s-info-group">
                <h3>Statistiken</h3>
                <div class="s-info-row"><span class="s-info-label">Sessions</span><span class="s-info-value">${d.total_sessions.toLocaleString('de-DE')}</span></div>
                <div class="s-info-row"><span class="s-info-label">Messages</span><span class="s-info-value">${d.total_messages.toLocaleString('de-DE')}</span></div>
                <div class="s-info-row"><span class="s-info-label">Modell-Preise</span><span class="s-info-value">${d.pricing_models}</span></div>
            </div>`;
    } catch(e) { console.error(e); }
}

// Init
loadPricing();
