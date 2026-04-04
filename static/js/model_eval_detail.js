/**
 * Sprint E2: Model Eval Detail — Layer-Tabs, Score-Tabellen, Layer-Formulare.
 * Wird von model_eval.js geladen, nutzt _criteria und api aus dem globalen Scope.
 */

// --- Detail Panel ---

async function showDetail(runId) {
    _activeRunId = runId;
    const panel = document.getElementById('evalDetail');
    try {
        const run = await api.get(`/api/eval/runs/${runId}`);
        panel.innerHTML = renderDetail(run);
        panel.style.display = '';
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (e) {
        panel.innerHTML = '<p style="color:#f66">Fehler beim Laden</p>';
        panel.style.display = '';
    }
}

function renderDetail(run) {
    const cm = {};
    _criteria.forEach(c => { cm[c.key] = c; });
    return `
        <div class="eval-detail__header">
            <div>
                <h3 style="margin:0;font-size:1rem">${escapeHtml(run.task_title)}</h3>
                <small style="color:#999">${escapeHtml(run.project_id || '')} &middot; ${run.created_at ? formatDate(run.created_at) : ''}</small>
            </div>
            <button class="btn btn-sm btn-ghost" onclick="document.getElementById('evalDetail').style.display='none'">&times;</button>
        </div>
        ${run.task_description ? `<p style="margin:0.5rem 0;font-size:0.85rem;color:#ccc">${escapeHtml(run.task_description)}</p>` : ''}
        ${run.notes ? `<p style="margin:0.25rem 0;font-size:0.8rem;color:#999"><em>${escapeHtml(run.notes)}</em></p>` : ''}
        <div class="eval-detail__scores">
            ${renderModelColumn(run, 'a', cm)}
            ${renderModelColumn(run, 'b', cm)}
        </div>
        ${run.winner ? `<p style="margin-top:0.75rem;font-size:0.85rem">Winner: ${winnerBadge(run.winner, run.model_a, run.model_b)}</p>` : ''}
    `;
}

function renderModelColumn(run, side, cm) {
    const model = run[`model_${side}`];
    if (!model) return '';
    const total = run[`total_score_${side}`];
    const finalTotal = run[`final_total_score_${side}`];
    const finalScores = run[`final_scores_${side}`];
    const judgeScores = run[`judge_scores_${side}`];
    const humanScores = run[`human_scores_${side}`];
    const swe = run[`swe_metrics_${side}`];
    const hasFinal = finalScores && finalScores.length;
    const displayTotal = hasFinal ? finalTotal : total;
    const tabId = `tabs_${side}`;

    const tabs = [
        { id: 'final', label: 'Final', active: true },
        { id: 'original', label: 'Original' },
        { id: 'judge', label: 'Judge' },
        { id: 'human', label: 'Human' },
        { id: 'swe', label: 'SWE' },
    ];

    return `<div class="eval-detail__model-col">
        <h4>${escapeHtml(model)} ${scoreBadge(displayTotal)}
            ${hasFinal && finalTotal !== total ? `<small style="color:#999;font-weight:400">(orig: ${total != null ? total.toFixed(1) : '-'})</small>` : ''}
        </h4>
        <div class="eval-tabs" id="${tabId}">
            ${tabs.map(t => `<button class="eval-tab${t.active ? ' eval-tab--active' : ''}" onclick="switchTab('${tabId}','${t.id}')">${t.label}</button>`).join('')}
        </div>
        <div class="eval-tab-content" data-tab-group="${tabId}">
            <div data-tab="final" style="display:block">${renderFinalTable(finalScores, cm)}</div>
            <div data-tab="original" style="display:none">${renderScoreTable(run[`scores_${side}`], cm, 'comment')}</div>
            <div data-tab="judge" style="display:none">
                ${judgeScores ? renderJudgeTable(judgeScores, cm) : '<p style="color:#666;font-size:0.8rem">Keine Judge-Scores</p>'}
                ${renderLayerForm('judge', run.id, side, 'Judge-Scores setzen', 'submitJudgeScores')}
            </div>
            <div data-tab="human" style="display:none">
                ${humanScores ? renderScoreTable(humanScores, cm, 'comment') : '<p style="color:#666;font-size:0.8rem">Keine Human-Overrides</p>'}
                ${renderLayerForm('human', run.id, side, 'Human-Override setzen', 'submitHumanScores')}
            </div>
            <div data-tab="swe" style="display:none">
                ${swe ? renderSWEDetail(swe) : '<p style="color:#666;font-size:0.8rem">Keine SWE-Metriken</p>'}
                ${renderSWEForm(run.id, side, swe)}
            </div>
        </div>
    </div>`;
}

function switchTab(groupId, tabId) {
    const group = document.querySelector(`[data-tab-group="${groupId}"]`);
    if (!group) return;
    group.querySelectorAll('[data-tab]').forEach(el => { el.style.display = 'none'; });
    const target = group.querySelector(`[data-tab="${tabId}"]`);
    if (target) target.style.display = 'block';
    const tabBar = document.getElementById(groupId);
    if (tabBar) {
        tabBar.querySelectorAll('.eval-tab').forEach(btn => btn.classList.remove('eval-tab--active'));
        const active = tabBar.querySelector(`.eval-tab[onclick*="'${tabId}'"]`);
        if (active) active.classList.add('eval-tab--active');
    }
}

// --- Score Tables ---

function renderFinalTable(scores, cm) {
    if (!scores || !scores.length) return '<p style="color:#666;font-size:0.8rem">Keine Final-Scores</p>';
    return `<table class="eval-table eval-table--compact">
        <thead><tr><th>Kriterium</th><th>Gewicht</th><th>Punkte</th><th>Herkunft</th></tr></thead>
        <tbody>${scores.map(s => {
            const c = cm[s.criterion_key] || {};
            const pts = ((s.score / 5) * s.weight).toFixed(1);
            return `<tr>
                <td>${escapeHtml(c.label || s.criterion_key)}</td>
                <td>${s.weight}%</td>
                <td><strong>${s.score}/5</strong> <small style="color:#999">(${pts})</small></td>
                <td><span class="source-tag source-tag--${s.source}">${s.source}</span></td>
            </tr>`;
        }).join('')}</tbody>
    </table>`;
}

function renderScoreTable(scores, cm, field) {
    if (!scores || !scores.length) return '<p style="color:#666;font-size:0.8rem">Keine Scores</p>';
    return `<table class="eval-table eval-table--compact">
        <thead><tr><th>Kriterium</th><th>Score</th><th>Kommentar</th></tr></thead>
        <tbody>${scores.map(s => {
            const c = cm[s.criterion_key] || {};
            return `<tr>
                <td>${escapeHtml(c.label || s.criterion_key)}</td>
                <td><strong>${s.score}/5</strong></td>
                <td style="white-space:normal;max-width:20rem">${escapeHtml(s[field] || '-')}</td>
            </tr>`;
        }).join('')}</tbody>
    </table>`;
}

function renderJudgeTable(scores, cm) {
    return `<table class="eval-table eval-table--compact">
        <thead><tr><th>Kriterium</th><th>Score</th><th>Rationale</th><th>Conf.</th></tr></thead>
        <tbody>${scores.map(s => {
            const c = cm[s.criterion_key] || {};
            return `<tr>
                <td>${escapeHtml(c.label || s.criterion_key)}</td>
                <td><strong>${s.score}/5</strong></td>
                <td style="white-space:normal;max-width:20rem">${escapeHtml(s.rationale || '-')}</td>
                <td>${s.confidence != null ? (s.confidence * 100).toFixed(0) + '%' : '-'}</td>
            </tr>`;
        }).join('')}</tbody>
    </table>`;
}

function renderSWEDetail(m) {
    const items = [
        ['Tests OK', m.tests_passed, m.tests_passed > 0 ? 'swe-val--ok' : ''],
        ['Tests Fail', m.tests_failed, m.tests_failed > 0 ? 'swe-val--fail' : ''],
        ['Files', m.files_changed, ''],
        ['+Lines', m.lines_added, ''],
        ['-Lines', m.lines_removed, ''],
        ['Lint', m.lint_warnings, m.lint_warnings > 0 ? 'swe-val--warn' : ''],
        ['Type Err', m.type_errors, m.type_errors > 0 ? 'swe-val--fail' : ''],
        ['Build', m.build_success != null ? (m.build_success ? 'OK' : 'FAIL') : null,
         m.build_success === true ? 'swe-val--ok' : m.build_success === false ? 'swe-val--fail' : ''],
    ].filter(([, v]) => v != null);
    if (!items.length) return '';
    return `<div class="swe-metrics-grid">${
        items.map(([l, v, cls]) => `<div class="swe-metric"><span class="swe-metric__label">${l}</span><span class="swe-metric__value ${cls}">${v}</span></div>`).join('')
    }</div>`;
}

// --- Layer Forms (dedupliziert) ---

function renderLayerForm(type, runId, side, label, submitFn) {
    const inputsId = `${type}Inputs_${side}_${runId}`;
    return `
    <details class="eval-layer-form">
        <summary class="eval-layer-form__toggle">${label}</summary>
        <div class="eval-layer-form__body">
            <div class="eval-scores-grid" id="${inputsId}">
                ${_criteria.map(c => `
                    <div class="eval-score-item">
                        <span class="eval-score-item__label">${escapeHtml(c.label)}</span>
                        <select data-key="${c.key}">
                            <option value="">-</option>
                            ${[0,1,2,3,4,5].map(v => `<option value="${v}">${v}</option>`).join('')}
                        </select>
                    </div>
                `).join('')}
            </div>
            <div style="margin-top:0.5rem"><button class="btn btn-sm btn-primary" onclick="${submitFn}(${runId},'${side}')">Speichern</button></div>
        </div>
    </details>`;
}

function renderSWEForm(runId, side, existing) {
    const v = existing || {};
    const fields = [
        ['tests_passed', 'Tests OK'], ['tests_failed', 'Tests Fail'],
        ['files_changed', 'Files'], ['lines_added', '+Lines'],
        ['lines_removed', '-Lines'], ['lint_warnings', 'Lint'],
        ['type_errors', 'Type Err'],
    ];
    return `
    <details class="eval-layer-form">
        <summary class="eval-layer-form__toggle">SWE-Metriken ${existing ? 'bearbeiten' : 'setzen'}</summary>
        <div class="eval-layer-form__body">
            <div class="eval-form__grid" id="sweInputs_${side}_${runId}" style="grid-template-columns:repeat(4,1fr)">
                ${fields.map(([f, l]) => `<div class="eval-form__field"><label class="eval-form__label">${l}</label><input type="number" data-field="${f}" value="${v[f] ?? ''}" min="0"></div>`).join('')}
                <div class="eval-form__field"><label class="eval-form__label">Build OK</label>
                    <select data-field="build_success">
                        <option value="">-</option>
                        <option value="true" ${v.build_success === true ? 'selected' : ''}>Ja</option>
                        <option value="false" ${v.build_success === false ? 'selected' : ''}>Nein</option>
                    </select>
                </div>
            </div>
            <div style="margin-top:0.5rem"><button class="btn btn-sm btn-primary" onclick="submitSWEMetrics(${runId},'${side}')">Speichern</button></div>
        </div>
    </details>`;
}

// --- Layer Submit ---

async function submitJudgeScores(runId, side) {
    const scores = collectLayerScores(`judgeInputs_${side}_${runId}`);
    if (!scores.length) { alert('Mindestens ein Judge-Score erforderlich.'); return; }
    try {
        await api.put(`/api/eval/runs/${runId}/judge-scores`, { model_side: side, scores });
        await showDetail(runId);
        await loadRuns();
    } catch (e) { alert('Fehler: ' + (e.message || e)); }
}

async function submitHumanScores(runId, side) {
    const scores = collectLayerScores(`humanInputs_${side}_${runId}`);
    if (!scores.length) { alert('Mindestens ein Human-Score erforderlich.'); return; }
    try {
        await api.put(`/api/eval/runs/${runId}/human-scores`, { model_side: side, scores });
        await showDetail(runId);
        await loadRuns();
    } catch (e) { alert('Fehler: ' + (e.message || e)); }
}

async function submitSWEMetrics(runId, side) {
    const container = document.getElementById(`sweInputs_${side}_${runId}`);
    if (!container) return;
    const metrics = {};
    container.querySelectorAll('[data-field]').forEach(el => {
        const val = el.value.trim();
        if (val === '') return;
        metrics[el.dataset.field] = el.dataset.field === 'build_success' ? val === 'true' : parseInt(val, 10);
    });
    if (!Object.keys(metrics).length) { alert('Mindestens eine Metrik erforderlich.'); return; }
    try {
        await api.put(`/api/eval/runs/${runId}/swe-metrics`, { model_side: side, metrics });
        await showDetail(runId);
        await loadRuns();
    } catch (e) { alert('Fehler: ' + (e.message || e)); }
}

function collectLayerScores(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    const scores = [];
    container.querySelectorAll('select[data-key]').forEach(sel => {
        if (sel.value !== '') scores.push({ criterion_key: sel.dataset.key, score: parseInt(sel.value, 10) });
    });
    return scores;
}
