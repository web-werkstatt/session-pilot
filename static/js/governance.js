/* Sprint 12: AI Governance - Overview Page */

let _govData = null;
let _editProject = null;
let _editLevel = 1;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadGovernanceOverview();
});

// --- Tabs ---
function showGovTab(tab) {
    document.querySelectorAll('.gov-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    document.querySelectorAll('.gov-tab-content').forEach(c => c.classList.toggle('active', c.id === 'tab-' + tab));
}

// --- Overview ---
async function loadGovernanceOverview() {
    try {
        const data = await api.get('/api/governance/overview');
        _govData = data;
        const projects = Array.isArray(data.projects) ? data.projects : [];
        const gateEntries = await Promise.all(projects.map(async function(project) {
            try {
                const gate = await api.get('/api/governance/gate/' + encodeURIComponent(project.name));
                return [project.name, gate];
            } catch (e) {
                return [project.name, { status: 'unknown', reasons: ['Gate nicht verfuegbar'] }];
            }
        }));
        const gateMap = {};
        gateEntries.forEach(function(entry) {
            gateMap[entry[0]] = entry[1];
        });
        renderKPIs(data);
        renderTable(projects, gateMap);
    } catch (e) {
        console.error('Governance load error:', e);
    }
}

function renderKPIs(data) {
    const s = data.summary || {};
    const total = (s.sandbox || 0) + (s.controlled || 0) + (s.critical || 0);
    document.getElementById('govTotalProjects').textContent = total;
    document.getElementById('govSandbox').textContent = s.sandbox || 0;
    document.getElementById('govControlled').textContent = s.controlled || 0;
    document.getElementById('govCritical').textContent = s.critical || 0;
    document.getElementById('govUnreviewed').textContent = data.unreviewed_critical || 0;
}

function renderGovStatus(gate) {
    const status = gate && gate.status ? gate.status : 'unknown';
    const config = {
        green: { label: 'OK', cls: 'green' },
        yellow: { label: 'Pruefen', cls: 'yellow' },
        red: { label: 'Kritisch', cls: 'red' },
        unknown: { label: 'Unklar', cls: 'unknown' },
    }[status] || { label: 'Unklar', cls: 'unknown' };
    return `<span class="gov-status-pill gov-status-pill--${config.cls}">${config.label}</span>`;
}

function getGovReasons(gate) {
    if (!gate || !Array.isArray(gate.reasons) || !gate.reasons.length) return ['Keine Gruende verfuegbar'];
    return gate.reasons.slice(0, 3);
}

function describePolicy(project) {
    const level = project && project.level_name ? project.level_name : 'sandbox';
    const config = {
        sandbox: { title: 'Sandbox', copy: 'AI darf frei schreiben und deployen.' },
        controlled: { title: 'Controlled', copy: 'Schreiben erlaubt, Review sinnvoll, kein Deploy.' },
        critical: { title: 'Critical', copy: 'Nur mit Kontrolle, kein freies Schreiben.' },
    }[level] || { title: level, copy: '' };
    return `<div class="gov-policy-cell"><span class="policy-badge policy-badge--${level}">${config.title}</span><div class="gov-policy-copy">${config.copy}</div></div>`;
}

function renderActivity(project) {
    const reworkClass = project.rework_rate >= 20 ? 'rework-high' : project.rework_rate >= 10 ? 'rework-medium' : 'rework-low';
    const lastTouch = project.last_ai_touch ? formatTimeAgo(project.last_ai_touch) : 'Kein AI-Touch';
    return `<div class="gov-activity-cell"><div class="${reworkClass}">${project.rework_rate.toFixed(1)}% Rework</div><div class="gov-activity-copy">${lastTouch} · ${project.rules_applied_count || 0} Rules</div></div>`;
}

function getGovAction(project, gate) {
    const status = gate && gate.status ? gate.status : 'unknown';
    if (status === 'red') return 'Jetzt pruefen';
    if (status === 'yellow') return 'Projekt checken';
    if (project.level >= 3) return 'Policy ansehen';
    return 'Details';
}

function renderTable(projects, gateMap) {
    const tbody = document.getElementById('govTableBody');
    if (!projects || !projects.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No projects with policy data.</td></tr>';
        return;
    }
    tbody.innerHTML = projects.map(p => {
        const gate = gateMap && gateMap[p.name] ? gateMap[p.name] : { status: 'unknown', reasons: ['Gate nicht verfuegbar'] };
        const reasons = getGovReasons(gate);
        const actionLabel = getGovAction(p, gate);

        return `<tr>
            <td>
                <div class="gov-project-cell">
                    <a href="/project/${encodeURIComponent(p.name)}" class="gov-project-link">${escapeHtml(p.name)}</a>
                </div>
            </td>
            <td>${renderGovStatus(gate)}</td>
            <td>
                <div class="gov-reasons">
                    ${reasons.map(reason => `<div class="gov-reason-line">${escapeHtml(reason)}</div>`).join('')}
                </div>
            </td>
            <td>${describePolicy(p)}</td>
            <td>${renderActivity(p)}</td>
            <td>
                <div class="gov-actions">
                    <a href="/project/${encodeURIComponent(p.name)}" class="btn btn-sm btn-secondary">${actionLabel}</a>
                    <button class="btn btn-sm btn-ghost" onclick="openPolicyModal('${escapeHtml(p.name)}', ${p.level})">Policy</button>
                </div>
            </td>
        </tr>`;
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

// --- Policy Modal ---
function openPolicyModal(project, currentLevel) {
    _editProject = project;
    document.getElementById('policyModalProject').textContent = project;
    document.getElementById('policyNotes').value = '';
    selectPolicyLevel(currentLevel);
    openModal('policyModal');
}

function selectPolicyLevel(level) {
    _editLevel = level;
    document.querySelectorAll('#policyToggle .policy-toggle__btn').forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.level) === level);
    });
    const details = document.getElementById('policyDetails');
    const info = {
        1: { name: 'Sandbox', desc: 'AI kann frei schreiben und deployen. Gut fuer Experimente und unkritische Projekte.', restrictions: 'Write: Yes | Review: No | Deploy: Yes' },
        2: { name: 'Controlled', desc: 'AI darf schreiben, aber Review sollte vor Merge stattfinden. Deploys sind aus.', restrictions: 'Write: Yes | Review: Required | Deploy: No' },
        3: { name: 'Critical', desc: 'AI sollte hier primaer planen und reviewen. Freies Schreiben nur mit bewusster Freigabe.', restrictions: 'Write: No | Review: Required | Deploy: No' },
    }[level];
    details.innerHTML = `<p><strong>${info.name}:</strong> ${info.desc}</p><p style="color:var(--text-muted);font-size:var(--text-xs);margin-top:var(--space-2)">${info.restrictions}</p>`;
}

async function savePolicy() {
    if (!_editProject) return;
    try {
        await api.put(`/api/projects/${encodeURIComponent(_editProject)}/policy`, {
            level: _editLevel,
            notes: document.getElementById('policyNotes').value.trim() || null,
        });
        closeModal('policyModal');
        loadGovernanceOverview();
    } catch (e) {
        alert('Error saving policy: ' + e.message);
    }
}

// --- Feedback Loop ---
async function loadFeedbackLoop() {
    try {
        const data = await api.get('/api/governance/feedback-loop');
        renderFeedbackLoop(data);
    } catch (e) {
        document.getElementById('feedbackContent').innerHTML = `<p class="text-muted">Error loading feedback data.</p>`;
    }
}

function renderFeedbackLoop(data) {
    const container = document.getElementById('feedbackContent');
    const levels = ['critical', 'controlled', 'sandbox'];
    const levelLabels = { sandbox: 'Sandbox', controlled: 'Controlled', critical: 'Critical' };
    const levelColors = { sandbox: 'var(--status-success)', controlled: 'var(--status-warning)', critical: 'var(--status-error)' };

    let html = '';
    for (const level of levels) {
        const info = data[level];
        if (!info) continue;
        const reasons = info.top_reasons || [];
        html += `<section class="feedback-level">
            <div class="feedback-level__header">
                <div>
                    <span class="policy-badge policy-badge--${level}">${levelLabels[level]}</span>
                    <div class="feedback-level__count">${info.project_count} projects</div>
                </div>
            </div>`;
        if (reasons.length === 0) {
            html += '<p class="text-muted" style="font-size:var(--text-sm)">No outcome data available.</p>';
        } else {
            for (const r of reasons) {
                html += `<div class="feedback-bar">
                    <span class="feedback-bar__label">${escapeHtml(r.reason.replace(/_/g, ' '))}</span>
                    <div class="feedback-bar__track">
                        <div class="feedback-bar__fill" style="width:${r.percentage}%;background:${levelColors[level]}"></div>
                    </div>
                    <span class="feedback-bar__pct">${r.percentage}%</span>
                </div>`;
            }
            if (reasons[0] && reasons[0].suggestion) {
                html += `<p class="feedback-level__suggestion">Empfehlung: ${escapeHtml(reasons[0].suggestion)}</p>`;
            }
        }
        html += '</section>';
    }
    container.innerHTML = html || '<p class="text-muted">No data available.</p>';
}
