/* Sprint 12: AI Governance */

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
        populateProjectSelects(data.projects);
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
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No projects with policy data.</td></tr>';
        return;
    }
    tbody.innerHTML = projects.map(p => {
        const reworkClass = p.rework_rate >= 20 ? 'rework-high' : p.rework_rate >= 10 ? 'rework-medium' : 'rework-low';
        const updated = p.updated_at ? formatTimeAgo(p.updated_at) : '-';
        return `<tr>
            <td><a href="/project/${encodeURIComponent(p.name)}" style="color:var(--accent-link)">${escapeHtml(p.name)}</a></td>
            <td><span class="policy-badge policy-badge--${p.level_name}">${p.level_name}</span></td>
            <td class="${reworkClass}">${p.rework_rate.toFixed(1)}%</td>
            <td>${p.rules_applied_count || 0}</td>
            <td>${updated}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick="openPolicyModal('${escapeHtml(p.name)}', ${p.level})">Edit</button>
                <button class="btn btn-sm btn-ghost" onclick="showEffectiveness('${escapeHtml(p.name)}')" title="Rule Effectiveness">
                    <i data-lucide="bar-chart-2" class="icon icon-sm"></i>
                </button>
            </td>
        </tr>`;
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function populateProjectSelects(projects) {
    const selects = ['ruleProjectSelect', 'snippetProjectSelect'];
    const opts = projects.map(p => `<option value="${escapeHtml(p.name)}">${escapeHtml(p.name)}</option>`).join('');
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = '<option value="">Select Project...</option>' + opts;
    });
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

// --- Rule Suggestions ---
async function loadRuleSuggestions(project) {
    const container = document.getElementById('rulesList');
    if (!project) {
        container.innerHTML = '<p class="text-muted">Select a project to see rule suggestions.</p>';
        return;
    }
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    try {
        const period = document.getElementById('rulePeriodSelect').value;
        const data = await api.get(`/api/governance/rules/${encodeURIComponent(project)}?period=${period}`);
        if (!data.rules || !data.rules.length) {
            container.innerHTML = '<p class="text-muted">No rule suggestions. Either too few sessions or no recurring issues found.</p>';
            return;
        }
        container.innerHTML = data.rules.map(r => `
            <div class="rule-card">
                <div class="rule-card__header">
                    <div>
                        <span class="rule-card__reason">${escapeHtml(r.reason.replace(/_/g, ' '))}</span>
                        <span class="rule-card__count">${r.count} occurrences</span>
                    </div>
                    <span class="rule-card__confidence confidence--${r.confidence}">${r.confidence}</span>
                </div>
                <div class="rule-card__body">${escapeHtml(r.rule)}</div>
                <div class="rule-card__diff">+ ${escapeHtml(r.claude_md)}</div>
                <div class="rule-card__actions">
                    <button class="btn btn-sm btn-primary" onclick="applyRule('${escapeHtml(project)}', '${escapeHtml(r.reason)}', '${escapeHtml(r.claude_md)}')">Apply to project.json</button>
                    <button class="btn btn-sm btn-secondary" onclick="copySnippet('${escapeHtml(r.claude_md)}')">Copy</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error: ${escapeHtml(e.message)}</p>`;
    }
}

async function applyRule(project, reason, ruleText) {
    try {
        await api.post(`/api/governance/rules/${encodeURIComponent(project)}/apply`, {
            reason: reason,
            rule_text: ruleText,
        });
        loadRuleSuggestions(project);
        loadGovernanceOverview();
    } catch (e) {
        alert('Error applying rule: ' + e.message);
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

// --- Snippets ---
async function loadSnippets(project) {
    const container = document.getElementById('snippetsContent');
    if (!project) {
        container.innerHTML = '<p class="text-muted">Select a project to generate export snippets.</p>';
        return;
    }
    try {
        const data = await api.get(`/api/governance/snippets/${encodeURIComponent(project)}`);
        let html = '';
        if (data.claude_md) {
            html += renderSnippetBox('CLAUDE.md', data.claude_md);
        }
        if (data.agents_md) {
            html += renderSnippetBox('AGENTS.md', data.agents_md);
        }
        if (data.pre_commit) {
            html += renderSnippetBox('pre-commit Hook', data.pre_commit);
        }
        container.innerHTML = html || '<p class="text-muted">No snippets generated for this policy level.</p>';
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error: ${escapeHtml(e.message)}</p>`;
    }
}

function renderSnippetBox(label, content) {
    const id = 'snippet_' + label.replace(/[^a-z]/gi, '');
    return `<div class="snippet-box">
        <div class="snippet-box__label">${escapeHtml(label)}</div>
        <button class="snippet-box__copy" onclick="copySnippet(document.getElementById('${id}').textContent)">Copy</button>
        <pre class="snippet-box__content" id="${id}">${escapeHtml(content)}</pre>
    </div>`;
}

// --- Effectiveness ---
async function showEffectiveness(project) {
    document.getElementById('effectivenessProject').textContent = project;
    const container = document.getElementById('effectivenessContent');
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    openModal('effectivenessModal');

    try {
        const data = await api.get(`/api/governance/effectiveness/${encodeURIComponent(project)}`);
        const items = data.effectiveness || [];
        if (!items.length) {
            container.innerHTML = '<p class="text-muted">No applied rules found for this project.</p>';
            return;
        }
        container.innerHTML = items.map(e => `
            <div class="eff-row">
                <div class="eff-label">
                    ${escapeHtml(e.rule_text)}
                    <span class="eff-verdict eff-verdict--${e.verdict}">${e.verdict}</span>
                </div>
                <div class="eff-stats">
                    <span>Before: ${e.before_pct}% (${e.before_total} sessions)</span>
                    <span>After: ${e.after_pct}% (${e.after_total} sessions)</span>
                    <span>Change: ${e.diff_pp > 0 ? '+' : ''}${e.diff_pp}pp</span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error: ${escapeHtml(e.message)}</p>`;
    }
}

// --- Helpers ---
function copySnippet(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Brief visual feedback
        const btn = event.target.closest('.snippet-box__copy') || event.target;
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = orig, 1500);
    });
}
