/* Settings Page */

let pricingData = [];
let currentProvider = 'all';
let generalSettingsLoaded = false;
let badgeStylesData = {};

// === Tab Navigation ===
function switchTab(tab, btn) {
    document.querySelectorAll('.settings-section').forEach(s => s.style.display = 'none');
    document.querySelectorAll('.settings-tab').forEach(t => t.classList.remove('active'));
    document.getElementById('section-' + tab).style.display = '';
    btn.classList.add('active');

    if (tab === 'general' && !generalSettingsLoaded) loadGeneralSettings();
    if (tab === 'pricing' && !pricingData.length) loadPricing();
    if (tab === 'accounts') loadAccounts();
    if (tab === 'links') loadLinks();
    if (tab === 'system') loadSystem();
}

// === General ===
async function loadGeneralSettings() {
    try {
        const data = await api.get('/api/settings/general');
        document.getElementById('includeSelfProjectToggle').checked = !!data.include_self_project;
        badgeStylesData = Object.assign({}, data.account_badge_styles || {});
        renderBadgeStyles();
        document.getElementById('generalSettingsStatus').textContent = '';
        generalSettingsLoaded = true;
    } catch (e) {
        console.error(e);
    }
}

async function saveGeneralSettings() {
    const status = document.getElementById('generalSettingsStatus');
    const data = {
        include_self_project: document.getElementById('includeSelfProjectToggle').checked,
        account_badge_styles: collectBadgeStyles()
    };

    status.textContent = 'Speichert...';
    try {
        const response = await api.post('/api/settings/general', data);
        window.DASHBOARD_SETTINGS = response.settings || window.DASHBOARD_SETTINGS;
        badgeStylesData = Object.assign({}, (response.settings || {}).account_badge_styles || {});
        renderBadgeStyles();
        status.textContent = 'Gespeichert';
        setTimeout(() => { status.textContent = ''; }, 1500);
    } catch (e) {
        console.error(e);
        status.textContent = 'Fehler beim Speichern';
    }
}

function cancelGeneralSettings() {
    generalSettingsLoaded = false;
    loadGeneralSettings();
    const status = document.getElementById('generalSettingsStatus');
    if (status) { status.textContent = 'Abgebrochen'; setTimeout(() => { status.textContent = ''; }, 1200); }
}

function renderBadgeStyles() {
    const tbody = document.getElementById('badgeStylesBody');
    if (!tbody) return;
    const keys = Object.keys(badgeStylesData).sort();
    if (!keys.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#666;padding:20px">No badge styles configured.</td></tr>';
        return;
    }
    tbody.innerHTML = keys.map(key => {
        const style = badgeStylesData[key] || {};
        return `<tr>
            <td><input type="text" data-field="key" value="${esc(key)}" oninput="updateBadgeStylePreview(this)"></td>
            <td><input type="text" data-field="background" value="${esc(style.background || '')}" placeholder="rgba(...)" oninput="updateBadgeStylePreview(this)"></td>
            <td><input type="text" data-field="text" value="${esc(style.text || '')}" placeholder="#fff" oninput="updateBadgeStylePreview(this)"></td>
            <td><input type="text" data-field="border" value="${esc(style.border || '')}" placeholder="rgba(...)" oninput="updateBadgeStylePreview(this)"></td>
            <td><span class="account-badge" data-preview="1" style="${buildBadgeStyleInline(style)}">${esc(key)}</span></td>
            <td class="s-btn-group"><button class="s-btn s-btn-sm s-btn-del" onclick="deleteBadgeStyleRow(this)">&#10005;</button></td>
        </tr>`;
    }).join('');
}

function addBadgeStyleRow() {
    const tbody = document.getElementById('badgeStylesBody');
    if (!tbody) return;
    if (tbody.querySelector('td[colspan]')) tbody.innerHTML = '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" data-field="key" placeholder="hermes" oninput="updateBadgeStylePreview(this)"></td>
        <td><input type="text" data-field="background" placeholder="rgba(...)" oninput="updateBadgeStylePreview(this)"></td>
        <td><input type="text" data-field="text" placeholder="#fbbf24" oninput="updateBadgeStylePreview(this)"></td>
        <td><input type="text" data-field="border" placeholder="rgba(...)" oninput="updateBadgeStylePreview(this)"></td>
        <td><span class="account-badge" data-preview="1">preview</span></td>
        <td class="s-btn-group"><button class="s-btn s-btn-sm s-btn-del" onclick="deleteBadgeStyleRow(this)">&#10005;</button></td>`;
    tbody.prepend(tr);
    tr.querySelector('input').focus();
}

function deleteBadgeStyleRow(btn) {
    const tr = btn.closest('tr');
    if (tr) tr.remove();
    const tbody = document.getElementById('badgeStylesBody');
    if (tbody && !tbody.children.length) renderBadgeStyles();
}

function updateBadgeStylePreview(input) {
    const tr = input.closest('tr');
    if (!tr) return;
    const preview = tr.querySelector('[data-preview="1"]');
    if (!preview) return;
    const key = tr.querySelector('[data-field="key"]').value || 'preview';
    preview.textContent = key;
    preview.setAttribute('style', buildBadgeStyleInline({
        background: tr.querySelector('[data-field="background"]').value.trim(),
        text: tr.querySelector('[data-field="text"]').value.trim(),
        border: tr.querySelector('[data-field="border"]').value.trim()
    }));
}

function buildBadgeStyleInline(style) {
    const parts = [];
    if (style.background) parts.push('background:' + style.background);
    if (style.text) parts.push('color:' + style.text);
    if (style.border) parts.push('border-color:' + style.border);
    return parts.join(';');
}

function normalizeBadgeKey(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function collectBadgeStyles() {
    const rows = document.querySelectorAll('#badgeStylesBody tr');
    const result = {};
    rows.forEach(function(tr) {
        const keyInput = tr.querySelector('[data-field="key"]');
        if (!keyInput) return;
        const key = normalizeBadgeKey(keyInput.value);
        if (!key) return;
        result[key] = {
            background: tr.querySelector('[data-field="background"]').value.trim(),
            text: tr.querySelector('[data-field="text"]').value.trim(),
            border: tr.querySelector('[data-field="border"]').value.trim()
        };
    });
    return result;
}

// === Pricing ===
async function loadPricing() {
    try {
        pricingData = await api.get('/api/settings/pricing');
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
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#666;padding:20px">No models</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(p => `<tr data-id="${p.id}" oninput="markRowDirty(this)">
        <td><input type="text" value="${esc(p.model_pattern)}" data-field="model_pattern"></td>
        <td><input type="text" value="${esc(p.display_name || '')}" data-field="display_name"></td>
        <td><input type="text" value="${esc(p.provider || '')}" data-field="provider" class="input-sm"></td>
        <td><input type="number" step="0.01" value="${p.input_price}" data-field="input_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="${p.output_price}" data-field="output_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="${p.cache_read_factor}" data-field="cache_read_factor" class="input-xs"></td>
        <td><input type="number" step="0.01" value="${p.cache_create_factor}" data-field="cache_create_factor" class="input-xs"></td>
        <td class="s-btn-group">
            <button class="s-btn s-btn-sm s-btn-del" onclick="markRowForDelete(this)" title="Zum Loeschen markieren">&#10005;</button>
        </td>
    </tr>`).join('');
}

/* Phase 7 (2026-04-14): Dirty-Tracking + Batch-Save/Cancel (fuer Pricing und Links). */
function markRowDirty(tr) {
    if (!tr.dataset.deleted) tr.dataset.dirty = '1';
}

function markRowForDelete(btn) {
    const tr = btn.closest('tr');
    if (!tr) return;
    if (tr.dataset.deleted === '1') {
        // Ruecknahme: Markierung entfernen
        delete tr.dataset.deleted;
        tr.style.opacity = '';
        tr.style.textDecoration = '';
        btn.innerHTML = '&#10005;';
        btn.title = 'Zum Loeschen markieren';
    } else if (!tr.dataset.id) {
        // Ungespeicherte Zeile direkt entfernen
        tr.remove();
    } else {
        tr.dataset.deleted = '1';
        tr.style.opacity = '0.45';
        tr.style.textDecoration = 'line-through';
        btn.innerHTML = '&#8634;'; // Undo-Zeichen
        btn.title = 'Loeschen zuruecknehmen';
    }
}

function esc(s) { return (s || '').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

function addPricingRow() {
    const tbody = document.getElementById('pricingBody');
    if (tbody.querySelector('td[colspan]')) tbody.innerHTML = '';
    const tr = document.createElement('tr');
    tr.dataset.id = '';
    tr.dataset.dirty = '1';
    tr.setAttribute('oninput', 'markRowDirty(this)');
    tr.innerHTML = `
        <td><input type="text" data-field="model_pattern" placeholder="e.g. gpt-6"></td>
        <td><input type="text" data-field="display_name" placeholder="GPT-6"></td>
        <td><input type="text" data-field="provider" placeholder="openai" class="input-sm"></td>
        <td><input type="number" step="0.01" value="3.00" data-field="input_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="15.00" data-field="output_price" class="input-xs"></td>
        <td><input type="number" step="0.01" value="0.10" data-field="cache_read_factor" class="input-xs"></td>
        <td><input type="number" step="0.01" value="1.25" data-field="cache_create_factor" class="input-xs"></td>
        <td class="s-btn-group">
            <button class="s-btn s-btn-sm s-btn-del" onclick="markRowForDelete(this)">&#10005;</button>
        </td>`;
    tbody.prepend(tr);
    tr.querySelector('input').focus();
}

async function saveAllPricing() {
    const status = document.getElementById('pricingStatus');
    const rows = [...document.querySelectorAll('#pricingBody tr')].filter(tr => !tr.querySelector('td[colspan]'));
    const saves = [];
    const deletes = [];

    rows.forEach(tr => {
        if (tr.dataset.deleted === '1' && tr.dataset.id) {
            deletes.push(parseInt(tr.dataset.id));
            return;
        }
        if (!tr.dataset.dirty && tr.dataset.id) return; // unveraendert
        const data = {id: tr.dataset.id ? parseInt(tr.dataset.id) : null};
        tr.querySelectorAll('input').forEach(inp => {
            data[inp.dataset.field] = inp.type === 'number' ? parseFloat(inp.value) : inp.value;
        });
        if (!data.model_pattern) return;
        saves.push(data);
    });

    status.textContent = 'Speichert...';
    try {
        for (const id of deletes) await api.del('/api/settings/pricing/' + id);
        for (const data of saves) await api.post('/api/settings/pricing', data);
        status.textContent = 'Gespeichert (' + saves.length + ' geaendert, ' + deletes.length + ' geloescht)';
        setTimeout(() => { status.textContent = ''; }, 2000);
        loadPricing();
    } catch (e) {
        console.error(e);
        status.textContent = 'Fehler beim Speichern';
    }
}

function cancelPricing() {
    loadPricing();
    const status = document.getElementById('pricingStatus');
    if (status) { status.textContent = 'Abgebrochen'; setTimeout(() => { status.textContent = ''; }, 1200); }
}

// === Accounts ===
async function loadAccounts() {
    try {
        const data = await api.get('/api/settings/accounts');

        document.getElementById('accountCards').innerHTML = data.map(a => {
            const badgeStyle = typeof getAccountBadgeStyle === 'function' ? getAccountBadgeStyle(a.name, a.tool) : '';
            const lastSession = a.last_session
                ? new Date(a.last_session).toLocaleDateString('en-US', {day:'2-digit',month:'2-digit',year:'numeric'})
                : 'Never';
            return `<div class="s-card">
                <div class="s-card-header">
                    <span class="s-card-name">${esc(a.name)}</span>
                    <span class="s-card-tool" style="${badgeStyle}">${a.tool}</span>
                </div>
                <div class="s-card-detail">${esc(a.config_dir)}</div>
                <div class="s-card-stat">
                    <div class="s-card-stat-item">
                        <div class="s-card-stat-value">${a.sessions}</div>
                        <div class="s-card-stat-label">Sessions</div>
                    </div>
                    <div class="s-card-stat-item">
                        <div class="s-card-stat-value">${lastSession}</div>
                        <div class="s-card-stat-label">Last Session</div>
                    </div>
                </div>
            </div>`;
        }).join('');

        if (!data.length) {
            document.getElementById('accountCards').innerHTML = '<div style="color:#666">No AI accounts detected.</div>';
        }
    } catch(e) { console.error(e); }
}

// === System ===
async function loadSystem() {
    try {
        const d = await api.get('/api/settings/system');

        document.getElementById('systemInfo').innerHTML = `
            <div class="s-info-group">
                <h3>Server</h3>
                <div class="s-info-row"><span class="s-info-label">Host</span><span class="s-info-value">${d.host}:${d.port}</span></div>
                <div class="s-info-row"><span class="s-info-label">Projects Path</span><span class="s-info-value">${esc(d.projects_dir)}</span></div>
                <div class="s-info-row"><span class="s-info-label">Gitea</span><span class="s-info-value">${esc(d.gitea_url)}</span></div>
                <div class="s-info-row"><span class="s-info-label">Gitea User</span><span class="s-info-value">${esc(d.gitea_user)}</span></div>
            </div>
            <div class="s-info-group">
                <h3>Database</h3>
                <div class="s-info-row"><span class="s-info-label">Host</span><span class="s-info-value">${d.db_host}:${d.db_port}</span></div>
                <div class="s-info-row"><span class="s-info-label">Name</span><span class="s-info-value">${esc(d.db_name)}</span></div>
                <div class="s-info-row"><span class="s-info-label">Size</span><span class="s-info-value">${d.db_size}</span></div>
            </div>
            <div class="s-info-group">
                <h3>Statistics</h3>
                <div class="s-info-row"><span class="s-info-label">Sessions</span><span class="s-info-value">${d.total_sessions.toLocaleString('en-US')}</span></div>
                <div class="s-info-row"><span class="s-info-label">Messages</span><span class="s-info-value">${d.total_messages.toLocaleString('en-US')}</span></div>
                <div class="s-info-row"><span class="s-info-label">Model Prices</span><span class="s-info-value">${d.pricing_models}</span></div>
            </div>`;
    } catch(e) { console.error(e); }
}

// === External Links ===
let linksData = [];

async function loadLinks() {
    try {
        linksData = await api.get('/api/settings/external-links');
        renderLinks();
    } catch(e) { console.error(e); }
}

function renderLinks() {
    const tbody = document.getElementById('linksBody');
    if (!linksData.length) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:#666;padding:20px">No external links configured. The sidebar section will be hidden.</td></tr>';
        return;
    }
    tbody.innerHTML = linksData.map(l => `<tr data-id="${l.id}" oninput="markRowDirty(this)">
        <td><input type="text" value="${esc(l.name)}" data-field="name"></td>
        <td><input type="text" value="${esc(l.url)}" data-field="url"></td>
        <td><input type="text" value="${esc(l.icon || 'external-link')}" data-field="icon" class="input-sm"></td>
        <td class="s-btn-group">
            <button class="s-btn s-btn-sm s-btn-del" onclick="markRowForDelete(this)" title="Zum Loeschen markieren">&#10005;</button>
        </td>
    </tr>`).join('');
}

function addLinkRow() {
    const tbody = document.getElementById('linksBody');
    if (tbody.querySelector('td[colspan]')) tbody.innerHTML = '';
    const tr = document.createElement('tr');
    tr.dataset.id = '';
    tr.dataset.dirty = '1';
    tr.setAttribute('oninput', 'markRowDirty(this)');
    tr.innerHTML = `
        <td><input type="text" data-field="name" placeholder="e.g. Portainer"></td>
        <td><input type="text" data-field="url" placeholder="https://..."></td>
        <td><input type="text" data-field="icon" placeholder="external-link" class="input-sm"></td>
        <td class="s-btn-group">
            <button class="s-btn s-btn-sm s-btn-del" onclick="markRowForDelete(this)">&#10005;</button>
        </td>`;
    tbody.prepend(tr);
    tr.querySelector('input').focus();
}

async function saveAllLinks() {
    const status = document.getElementById('linksStatus');
    const rows = [...document.querySelectorAll('#linksBody tr')].filter(tr => !tr.querySelector('td[colspan]'));
    const saves = [];
    const deletes = [];

    rows.forEach(tr => {
        if (tr.dataset.deleted === '1' && tr.dataset.id) {
            deletes.push(parseInt(tr.dataset.id));
            return;
        }
        if (!tr.dataset.dirty && tr.dataset.id) return;
        const data = {id: tr.dataset.id ? parseInt(tr.dataset.id) : null};
        tr.querySelectorAll('input').forEach(inp => { data[inp.dataset.field] = inp.value; });
        if (!data.name || !data.url) return;
        saves.push(data);
    });

    status.textContent = 'Speichert...';
    try {
        for (const id of deletes) await api.del('/api/settings/external-links/' + id);
        for (const data of saves) await api.post('/api/settings/external-links', data);
        status.textContent = 'Gespeichert (' + saves.length + ' geaendert, ' + deletes.length + ' geloescht)';
        setTimeout(() => { status.textContent = ''; }, 2000);
        loadLinks();
    } catch (e) {
        console.error(e);
        status.textContent = 'Fehler beim Speichern';
    }
}

function cancelLinks() {
    loadLinks();
    const status = document.getElementById('linksStatus');
    if (status) { status.textContent = 'Abgebrochen'; setTimeout(() => { status.textContent = ''; }, 1200); }
}

// Init
loadPricing();
