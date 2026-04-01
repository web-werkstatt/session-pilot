/* Sprint 12: AI Governance - Overview Page */

let _govData = null;
let _editProject = null;
let _editLevel = 1;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadGovernanceOverview();
    loadFeedbackLoop();
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
        renderKPIs(data);
        renderTable(data.projects);
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

function renderTable(projects) {
    const tbody = document.getElementById('govTableBody');
    if (!projects || !projects.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No projects with policy data.</td></tr>';
        return;
    }
    tbody.innerHTML = projects.map(p => {
        const reworkClass = p.rework_rate >= 20 ? 'rework-high' : p.rework_rate >= 10 ? 'rework-medium' : 'rework-low';
        const lastTouch = p.last_ai_touch ? formatTimeAgo(p.last_ai_touch) : '-';

        // Empfehlung bei hoher Rework-Rate und niedrigem Level
        let recommendation = '';
        if (p.rework_rate >= 20 && p.level < 3) {
            const nextLevel = p.level + 1;
            const nextName = {2: 'Controlled', 3: 'Critical'}[nextLevel];
            recommendation = `<div class="gov-recommendation" title="Rework-Rate ist hoch – strengeres Policy-Level empfohlen"><i data-lucide="alert-triangle" class="icon icon-sm"></i> Level auf '${nextName}' erhoehen?</div>`;
        } else if (p.rework_rate >= 15 && p.level === 1) {
            recommendation = `<div class="gov-recommendation gov-recommendation--mild" title="Rework-Rate ueber 15% – Policy-Level pruefen"><i data-lucide="info" class="icon icon-sm"></i> Level pruefen</div>`;
        }

        return `<tr>
            <td><a href="/project/${encodeURIComponent(p.name)}" style="color:var(--accent-link)">${escapeHtml(p.name)}</a></td>
            <td><span class="gov-health-badge" id="health-${CSS.escape(p.name)}" title="Loading...">...</span></td>
            <td><span class="policy-badge policy-badge--${p.level_name}">${p.level_name}</span>${recommendation}</td>
            <td class="${reworkClass}">${p.rework_rate.toFixed(1)}%</td>
            <td>${p.rules_applied_count || 0}</td>
            <td>${lastTouch}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="openPolicyModal('${escapeHtml(p.name)}', ${p.level})">Edit</button>
                <a href="/project/${encodeURIComponent(p.name)}" class="btn btn-sm btn-ghost" title="Details &amp; Rule Effectiveness">
                    <i data-lucide="external-link" class="icon icon-sm"></i>
                </a>
            </td>
        </tr>`;
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();

    // Health-Ampeln asynchron laden (nicht blockierend)
    _loadHealthBadges(projects);
}

async function _loadHealthBadges(projects) {
    const statusIcons = { green: '\u25CF', yellow: '\u25CF', red: '\u25CF' };
    for (const p of projects) {
        try {
            const gate = await api.get('/api/governance/gate/' + encodeURIComponent(p.name));
            const el = document.getElementById('health-' + CSS.escape(p.name));
            if (el) {
                el.className = 'gov-health-badge gov-health--' + gate.status;
                el.textContent = statusIcons[gate.status] || '?';
                el.title = gate.reasons.join('; ') || gate.status;
            }
        } catch (e) {
            const el = document.getElementById('health-' + CSS.escape(p.name));
            if (el) {
                el.className = 'gov-health-badge gov-health--unknown';
                el.textContent = '?';
                el.title = 'Gate nicht verfuegbar';
            }
        }
    }
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
        1: { name: 'Sandbox', desc: 'AI can write, refactor, and deploy freely. Best for experiments and prototypes.', restrictions: 'Write: Yes | Review: No | Deploy: Yes' },
        2: { name: 'Controlled', desc: 'AI can write code, but review is recommended before merge. No deployments.', restrictions: 'Write: Yes | Review: Required | Deploy: No' },
        3: { name: 'Critical', desc: 'AI should only review/plan. No writing without approval. No deployments.', restrictions: 'Write: No | Review: Required | Deploy: No' },
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
        html += `<div class="feedback-level">
            <div class="feedback-level__header">
                <span class="feedback-level__title" style="color:${levelColors[level]}">
                    <span class="policy-badge policy-badge--${level}">${levelLabels[level]}</span>
                </span>
                <span class="feedback-level__count">${info.project_count} projects</span>
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
                html += `<p style="font-size:var(--text-xs);color:var(--text-muted);margin-top:var(--space-2)">Suggestion: ${escapeHtml(reasons[0].suggestion)}</p>`;
            }
        }
        html += '</div>';
    }
    container.innerHTML = html || '<p class="text-muted">No data available.</p>';
}
