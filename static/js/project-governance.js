/* Project Detail: Governance Tab */

let governanceTabLoaded = false;

async function loadGovernanceTab() {
    governanceTabLoaded = true;
    const container = document.getElementById('governanceBody');
    try {
        const policy = await api.get(`/api/projects/${encodeURIComponent(PROJECT_NAME)}/policy`);
        const levelName = policy.level_name || 'sandbox';
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
                <div style="margin:var(--space-3) 0">
                    <span class="policy-badge policy-badge--${levelName}" style="font-size:0.85rem;padding:4px 12px">${levelName.toUpperCase()}</span>
                </div>
                <div style="font-size:var(--text-sm);color:var(--text-secondary)">
                    <p>Write: ${restrictions.allow_write ? '✓ Allowed' : '✗ Restricted'}</p>
                    <p>Review: ${restrictions.require_review ? '✓ Required' : '○ Optional'}</p>
                    <p>Deploy: ${restrictions.allow_deploy ? '✓ Allowed' : '✗ Restricted'}</p>
                </div>
                ${policy.notes ? `<p style="margin-top:var(--space-2);font-size:var(--text-xs);color:var(--text-muted)">${escapeHtml(policy.notes)}</p>` : ''}
                <button class="btn btn-sm btn-secondary" style="margin-top:var(--space-3)" onclick="window.location.href='/governance'">Manage in Governance</button>
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

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = `<p class="text-muted">Error loading governance data: ${escapeHtml(e.message)}</p>`;
    }
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
