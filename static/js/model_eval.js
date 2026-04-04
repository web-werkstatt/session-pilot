/**
 * Sprint E1/E2: Model Eval — Dashboard JS (Kern).
 * Detail-Rendering und Layer-Formulare in model_eval_detail.js.
 */

let _criteria = [];
let _runs = [];
let _activeRunId = null;

// --- Init ---

document.addEventListener('DOMContentLoaded', async () => {
    await loadCriteria();
    await loadRuns();

    const modelBInput = document.getElementById('evalModelB');
    if (modelBInput) {
        modelBInput.addEventListener('input', () => {
            const wrap = document.getElementById('scoresBWrap');
            if (wrap) wrap.style.display = modelBInput.value.trim() ? '' : 'none';
        });
    }
});

// --- Criteria ---

async function loadCriteria() {
    try {
        const data = await api.get('/api/eval/criteria');
        _criteria = data.criteria || [];
        renderScoreInputs('scoresA', _criteria);
        renderScoreInputs('scoresB', _criteria);
    } catch (e) {
        console.error('Criteria load failed:', e);
    }
}

function renderScoreInputs(containerId, criteria) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = criteria.map(c => `
        <div class="eval-score-item">
            <span class="eval-score-item__label">${escapeHtml(c.label)} <small>(${c.weight}%)</small></span>
            <select data-key="${c.key}">
                <option value="">-</option>
                ${[0,1,2,3,4,5].map(v => `<option value="${v}">${v}</option>`).join('')}
            </select>
        </div>
    `).join('');
}

// --- Runs Table ---

async function loadRuns() {
    const projectFilter = document.getElementById('evalFilterProject');
    const projectId = projectFilter ? projectFilter.value : '';
    const url = projectId ? `/api/eval/runs?project_id=${encodeURIComponent(projectId)}` : '/api/eval/runs';

    try {
        const data = await api.get(url);
        _runs = data.runs || [];
        renderTable(_runs);
        updateKPIs(_runs);
        populateProjectFilter(_runs);
    } catch (e) {
        console.error('Runs load failed:', e);
        document.getElementById('evalTableBody').innerHTML =
            '<tr><td colspan="10" style="text-align:center;color:#f66">Fehler beim Laden</td></tr>';
    }
}

function renderTable(runs) {
    const tbody = document.getElementById('evalTableBody');
    if (!runs.length) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:#666">Keine Eval-Runs vorhanden</td></tr>';
        return;
    }
    tbody.innerHTML = runs.map(r => {
        const finalA = r.final_total_score_a != null ? r.final_total_score_a : r.total_score_a;
        const finalB = r.final_total_score_b != null ? r.final_total_score_b : r.total_score_b;
        return `
        <tr style="cursor:pointer" onclick="showDetail(${r.id})">
            <td>${r.id}</td>
            <td>${escapeHtml(r.task_title)}</td>
            <td>${escapeHtml(r.project_id || '-')}</td>
            <td>${escapeHtml(r.model_a)}</td>
            <td>${scoreBadge(finalA)}</td>
            <td>${escapeHtml(r.model_b || '-')}</td>
            <td>${finalB != null ? scoreBadge(finalB) : '-'}</td>
            <td>${layerIndicators(r)}</td>
            <td>${winnerBadge(r.winner, r.model_a, r.model_b)}</td>
            <td>${r.created_at ? formatDate(r.created_at) : '-'}</td>
        </tr>`;
    }).join('');
}

function layerIndicators(r) {
    const dots = [];
    if (r.judge_total_score_a != null) dots.push('<span class="layer-dot layer-dot--judge" title="Judge">J</span>');
    if (r.human_total_score_a != null) dots.push('<span class="layer-dot layer-dot--human" title="Human">H</span>');
    return dots.length ? dots.join('') : '<span style="color:#555">-</span>';
}

function scoreBadge(score) {
    if (score == null) return '-';
    const s = parseFloat(score);
    let cls = 'score-badge--mid';
    if (s >= 75) cls = 'score-badge--high';
    else if (s < 50) cls = 'score-badge--low';
    return `<span class="score-badge ${cls}">${s.toFixed(1)}</span>`;
}

function winnerBadge(winner, modelA, modelB) {
    if (!winner) return '-';
    if (winner === 'tie') return '<span class="winner-badge winner-badge--tie">Tie</span>';
    if (winner === 'a') return `<span class="winner-badge winner-badge--a">${escapeHtml(modelA)}</span>`;
    return `<span class="winner-badge winner-badge--b">${escapeHtml(modelB || 'B')}</span>`;
}

function updateKPIs(runs) {
    document.getElementById('evalRunCount').textContent = runs.length;
    const scores = runs.map(r => r.final_total_score_a != null ? r.final_total_score_a : r.total_score_a).filter(s => s != null);
    const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : '-';
    document.getElementById('evalAvgScore').textContent = avg;

    const models = new Set();
    runs.forEach(r => { models.add(r.model_a); if (r.model_b) models.add(r.model_b); });
    document.getElementById('evalModelsCount').textContent = models.size;

    const withLayers = runs.filter(r => r.judge_total_score_a != null || r.human_total_score_a != null).length;
    document.getElementById('evalLayerCount').textContent = withLayers;
}

function populateProjectFilter(runs) {
    const select = document.getElementById('evalFilterProject');
    if (!select) return;
    const current = select.value;
    const projects = [...new Set(runs.map(r => r.project_id).filter(Boolean))].sort();
    select.innerHTML = '<option value="">Alle Projekte</option>' +
        projects.map(p => `<option value="${escapeHtml(p)}" ${p === current ? 'selected' : ''}>${escapeHtml(p)}</option>`).join('');
}

// --- Create ---

function toggleCreateForm() {
    const form = document.getElementById('evalCreateForm');
    form.style.display = form.style.display === 'none' ? '' : 'none';
}

function collectScores(containerId) {
    const selects = document.querySelectorAll(`#${containerId} select[data-key]`);
    const scores = [];
    selects.forEach(sel => {
        if (sel.value !== '') scores.push({ criterion_key: sel.dataset.key, score: parseInt(sel.value, 10) });
    });
    return scores;
}

async function submitEvalRun() {
    const taskTitle = document.getElementById('evalTaskTitle').value.trim();
    const modelA = document.getElementById('evalModelA').value.trim();
    const modelB = document.getElementById('evalModelB').value.trim();
    const scoresA = collectScores('scoresA');

    if (!taskTitle || !modelA) { alert('Task-Titel und Model A sind Pflichtfelder.'); return; }
    if (!scoresA.length) { alert('Mindestens ein Score fuer Model A ist erforderlich.'); return; }

    const body = {
        task_title: taskTitle, model_a: modelA, scores_a: scoresA,
        task_description: document.getElementById('evalDescription').value.trim() || null,
        project_id: document.getElementById('evalProjectId').value.trim() || null,
        notes: document.getElementById('evalNotes').value.trim() || null,
    };
    if (modelB) {
        const scoresB = collectScores('scoresB');
        if (!scoresB.length) { alert('Scores fuer Model B erforderlich.'); return; }
        body.model_b = modelB;
        body.scores_b = scoresB;
    }

    try {
        const result = await api.post('/api/eval/runs', body);
        toggleCreateForm();
        await loadRuns();
        showDetail(result.id);
    } catch (e) {
        alert('Fehler: ' + (e.message || e));
    }
}
