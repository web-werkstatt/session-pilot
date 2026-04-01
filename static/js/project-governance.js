/* Project Detail: Governance Tab */

let governanceTabLoaded = false;

async function loadGovernanceTab() {
    governanceTabLoaded = true;
    const container = document.getElementById('governanceBody');
    try {
        const policy = await api.get(`/api/projects/${encodeURIComponent(PROJECT_NAME)}/policy`);
        const restrictions = policy.restrictions || {};
        const rules = policy.rules_applied || [];
        const workflow = policy.preferred_workflow || {};

        const selOpt = (opts, current) => opts.map(o =>
            `<option value="${o.value}"${o.value === current ? ' selected' : ''}>${escapeHtml(o.label)}</option>`
        ).join('');

        let html = `
        <div style="display:grid;gap:var(--space-4);grid-template-columns:1fr 1fr">
            <div class="info-block">
                <h3>Policy Level</h3>
                <div class="policy-toggle" style="margin:var(--space-3) 0">
                    <button class="policy-toggle__btn policy-toggle__btn--sandbox${policy.level === 1 ? ' active' : ''}" onclick="setProjectPolicy(1)">Sandbox</button>
                    <button class="policy-toggle__btn policy-toggle__btn--controlled${policy.level === 2 ? ' active' : ''}" onclick="setProjectPolicy(2)">Controlled</button>
                    <button class="policy-toggle__btn policy-toggle__btn--critical${policy.level === 3 ? ' active' : ''}" onclick="setProjectPolicy(3)">Critical</button>
                </div>
                <div id="govPolicyRestrictions" style="font-size:var(--text-sm);color:var(--text-secondary)">
                    <p>Write: ${restrictions.allow_write ? '✓ Allowed' : '✗ Restricted'}</p>
                    <p>Review: ${restrictions.require_review ? '✓ Required' : '○ Optional'}</p>
                    <p>Deploy: ${restrictions.allow_deploy ? '✓ Allowed' : '✗ Restricted'}</p>
                </div>
                ${policy.notes ? `<p style="margin-top:var(--space-2);font-size:var(--text-xs);color:var(--text-muted)">${escapeHtml(policy.notes)}</p>` : ''}
                <div id="govPolicySaveStatus" class="wf-status"></div>
            </div>
            <div class="info-block">
                <h3>Workflow</h3>
                <div class="wf-grid">
                    <label class="wf-toggle">
                        <input type="checkbox" id="wfSprints" ${workflow.uses_sprints ? 'checked' : ''} onchange="saveWorkflow()">
                        <span>Use Sprints</span>
                    </label>
                    <div class="wf-field">
                        <label class="wf-label" for="wfReview">Session Review</label>
                        <select id="wfReview" class="wf-select" onchange="saveWorkflow()">
                            ${selOpt([
                                {value: 'none', label: 'None'},
                                {value: 'reminder', label: 'Reminder'},
                                {value: 'mandatory', label: 'Mandatory'},
                            ], workflow.require_session_review || 'none')}
                        </select>
                    </div>
                    <div class="wf-field">
                        <label class="wf-label" for="wfSessionEnd">Session End</label>
                        <select id="wfSessionEnd" class="wf-select" onchange="saveWorkflow()">
                            ${selOpt([
                                {value: 'free', label: 'Free'},
                                {value: 'commit_flow', label: 'Commit Flow'},
                            ], workflow.session_end_mode || 'free')}
                        </select>
                    </div>
                    <div class="wf-field">
                        <label class="wf-label" for="wfGovMode">Governance</label>
                        <select id="wfGovMode" class="wf-select" onchange="saveWorkflow()">
                            ${selOpt([
                                {value: 'relaxed', label: 'Relaxed'},
                                {value: 'balanced', label: 'Balanced'},
                                {value: 'strict', label: 'Strict'},
                            ], workflow.governance_mode || 'relaxed')}
                        </select>
                    </div>
                </div>
                <div id="wfSaveStatus" class="wf-status"></div>
            </div>
        </div>`;

        if (rules.length > 0) {
            html += '<div class="info-block" style="margin-top:var(--space-4)"><h3>Applied Rules</h3>';
            html += rules.map(r => `<div style="padding:var(--space-2) 0;border-bottom:1px solid var(--border-subtle);font-size:var(--text-sm)">
                <span style="color:var(--text-primary)">${escapeHtml(r.rule_text)}</span>
                <span style="color:var(--text-muted);font-size:var(--text-xs);margin-left:var(--space-2)">${r.reason} | ${formatTimeAgo(r.applied_at)}</span>
            </div>`).join('');
            html += '</div>';
        }

        // Collapsible Sections: Rule Suggestions, Effectiveness, Snippets
        html += _govSectionHtml('rules', 'Rule Suggestions',
            `<div style="margin-bottom:var(--space-3)">
                <select id="govRulePeriod" onchange="loadGovRuleSuggestions()" style="font-size:var(--text-sm);padding:2px 6px;border-radius:var(--radius);border:1px solid var(--border-subtle);background:var(--bg-surface);color:var(--text-primary)">
                    <option value="30d">Last 30 days</option>
                    <option value="90d" selected>Last 90 days</option>
                    <option value="180d">Last 180 days</option>
                </select>
            </div>
            <div id="govRulesList"><p class="text-muted">Click to load...</p></div>`);

        html += _govSectionHtml('effectiveness', 'Rule Effectiveness',
            '<div id="govEffectiveness"><p class="text-muted">Click to load...</p></div>');

        html += _govSectionHtml('snippets', 'Export Snippets',
            '<div id="govSnippets"><p class="text-muted">Click to load...</p></div>');

        container.innerHTML = html;
        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error loading governance data: ${escapeHtml(e.message)}</p>`;
    }
}

async function setProjectPolicy(level) {
    // Toggle-Buttons aktiv setzen
    document.querySelectorAll('.policy-toggle__btn').forEach(btn => {
        const btnLevel = {
            'policy-toggle__btn--sandbox': 1,
            'policy-toggle__btn--controlled': 2,
            'policy-toggle__btn--critical': 3,
        };
        const l = Object.entries(btnLevel).find(([cls]) => btn.classList.contains(cls));
        btn.classList.toggle('active', l && l[1] === level);
    });

    const status = document.getElementById('govPolicySaveStatus');
    try {
        status.textContent = 'Saving...';
        status.className = 'wf-status wf-status--saving';
        const updated = await api.put(`/api/projects/${encodeURIComponent(PROJECT_NAME)}/policy`, { level: level });
        // Restrictions-Anzeige aktualisieren
        const r = updated.restrictions || {};
        document.getElementById('govPolicyRestrictions').innerHTML =
            `<p>Write: ${r.allow_write ? '✓ Allowed' : '✗ Restricted'}</p>` +
            `<p>Review: ${r.require_review ? '✓ Required' : '○ Optional'}</p>` +
            `<p>Deploy: ${r.allow_deploy ? '✓ Allowed' : '✗ Restricted'}</p>`;
        status.textContent = 'Saved';
        status.className = 'wf-status wf-status--saved';
        setTimeout(() => { status.textContent = ''; status.className = 'wf-status'; }, 2000);
    } catch (e) {
        status.textContent = 'Error saving';
        status.className = 'wf-status wf-status--error';
    }
}

function _govSectionHtml(id, title, bodyHtml) {
    return `<div class="gov-section collapsed" id="govSec_${id}">
        <div class="gov-section-header" onclick="toggleGovSection('${id}')">
            <h3>${title}</h3>
            <i data-lucide="chevron-down" class="icon icon-sm gov-section-chevron"></i>
        </div>
        <div class="gov-section-body">${bodyHtml}</div>
    </div>`;
}

let _govLoaded = { rules: false, effectiveness: false, snippets: false };

function toggleGovSection(id) {
    const sec = document.getElementById('govSec_' + id);
    if (!sec) return;
    sec.classList.toggle('collapsed');
    if (!sec.classList.contains('collapsed') && !_govLoaded[id]) {
        _govLoaded[id] = true;
        if (id === 'rules') loadGovRuleSuggestions();
        else if (id === 'effectiveness') loadGovEffectiveness();
        else if (id === 'snippets') loadGovSnippets();
    }
}

// --- Rule Suggestions ---
async function loadGovRuleSuggestions() {
    const container = document.getElementById('govRulesList');
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    try {
        const period = document.getElementById('govRulePeriod').value;
        const data = await api.get(`/api/governance/rules/${encodeURIComponent(PROJECT_NAME)}?period=${period}`);
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
                    <button class="btn btn-sm btn-primary" onclick="applyGovRule('${escapeHtml(r.reason)}', '${escapeHtml(r.claude_md)}')">Apply to project.json</button>
                    <button class="btn btn-sm btn-secondary" onclick="copyGovSnippet('${escapeHtml(r.claude_md)}')">Copy</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error: ${escapeHtml(e.message)}</p>`;
    }
}

async function applyGovRule(reason, ruleText) {
    try {
        await api.post(`/api/governance/rules/${encodeURIComponent(PROJECT_NAME)}/apply`, {
            reason: reason,
            rule_text: ruleText,
        });
        // Reload entire tab to show new applied rule
        governanceTabLoaded = false;
        _govLoaded = { rules: false, effectiveness: false, snippets: false };
        loadGovernanceTab();
    } catch (e) {
        alert('Error applying rule: ' + e.message);
    }
}

// --- Rule Effectiveness ---
async function loadGovEffectiveness() {
    const container = document.getElementById('govEffectiveness');
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    try {
        const data = await api.get(`/api/governance/effectiveness/${encodeURIComponent(PROJECT_NAME)}`);
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

// --- Export Snippets ---
async function loadGovSnippets() {
    const container = document.getElementById('govSnippets');
    container.innerHTML = '<p class="text-muted">Loading...</p>';
    try {
        const data = await api.get(`/api/governance/snippets/${encodeURIComponent(PROJECT_NAME)}`);
        let html = '';
        if (data.claude_md) html += _govSnippetBox('CLAUDE.md', data.claude_md);
        if (data.agents_md) html += _govSnippetBox('AGENTS.md', data.agents_md);
        if (data.pre_commit) html += _govSnippetBox('pre-commit Hook', data.pre_commit);
        container.innerHTML = html || '<p class="text-muted">No snippets generated for this policy level.</p>';
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error: ${escapeHtml(e.message)}</p>`;
    }
}

function _govSnippetBox(label, content) {
    const id = 'govSnip_' + label.replace(/[^a-z]/gi, '');
    return `<div class="snippet-box">
        <div class="snippet-box__label">${escapeHtml(label)}</div>
        <button class="snippet-box__copy" onclick="copyGovSnippet(document.getElementById('${id}').textContent)">Copy</button>
        <pre class="snippet-box__content" id="${id}">${escapeHtml(content)}</pre>
    </div>`;
}

function copyGovSnippet(text) {
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target.closest('.snippet-box__copy, .btn') || event.target;
        const orig = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = orig, 1500);
    });
}

let _wfSaveTimer = null;
async function saveWorkflow() {
    clearTimeout(_wfSaveTimer);
    _wfSaveTimer = setTimeout(async () => {
        const status = document.getElementById('wfSaveStatus');
        try {
            status.textContent = 'Saving...';
            status.className = 'wf-status wf-status--saving';
            await api.patch(`/api/projects/${encodeURIComponent(PROJECT_NAME)}/workflow`, {
                uses_sprints: document.getElementById('wfSprints').checked,
                require_session_review: document.getElementById('wfReview').value,
                session_end_mode: document.getElementById('wfSessionEnd').value,
                governance_mode: document.getElementById('wfGovMode').value,
            });
            status.textContent = 'Saved';
            status.className = 'wf-status wf-status--saved';
            setTimeout(() => { status.textContent = ''; status.className = 'wf-status'; }, 2000);
        } catch (e) {
            status.textContent = 'Error saving';
            status.className = 'wf-status wf-status--error';
        }
    }, 400);
}
