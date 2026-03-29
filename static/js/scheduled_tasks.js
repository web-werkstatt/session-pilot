/**
 * Scheduled Tasks - CRUD und UI
 */
let allTasks = [];
let currentFilter = 'all';
let editingTaskId = null;
let templates = {};

// === Init ===
document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    loadTemplates();
});

// === Data Loading ===
function loadTasks() {
    api.get('/api/scheduled-tasks')
        .then(data => {
            allTasks = data.tasks || [];
            updateStats();
            renderTasks();
        })
        .catch(err => {
            console.error('Error loading:', err);
            document.getElementById('loading').innerHTML = '<div class="error">Error loading tasks</div>';
        });
}

function loadTemplates() {
    api.get('/api/scheduled-tasks/templates')
        .then(data => { templates = data; })
        .catch(() => {});
}

// === Stats ===
function updateStats() {
    const active = allTasks.filter(t => t.enabled).length;
    const paused = allTasks.filter(t => !t.enabled).length;
    const types = new Set(allTasks.map(t => t.type)).size;

    document.getElementById('totalTasks').textContent = allTasks.length;
    document.getElementById('activeTasks').textContent = active;
    document.getElementById('pausedTasks').textContent = paused;
    document.getElementById('typeCount').textContent = types;
}

// === Rendering ===
function renderTasks() {
    const filtered = currentFilter === 'all'
        ? allTasks
        : allTasks.filter(t => t.type === currentFilter);

    document.getElementById('loading').style.display = 'none';

    if (filtered.length === 0 && allTasks.length === 0) {
        document.getElementById('tasksTable').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
    }

    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('tasksTable').style.display = 'table';

    const tbody = document.getElementById('tasksBody');

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No tasks for this filter</td></tr>';
        return;
    }

    let html = '';
    filtered.forEach(task => {
        const statusClass = task.enabled ? 'active' : 'paused';
        const statusIcon = task.enabled ? 'play-circle' : 'pause-circle';
        const typeIcon = getTypeIcon(task.type);
        const lastRun = task.last_run
            ? formatTimeAgo(task.last_run)
            : '<span class="text-muted">Never</span>';
        const resultBadge = task.last_result
            ? `<span class="badge badge-${task.last_result === 'ok' ? 'success' : 'error'}">${task.last_result}</span>`
            : '';

        html += `
            <tr class="task-row ${statusClass}" onclick="showDetail('${task.id}')">
                <td>
                    <button class="status-toggle ${statusClass}" onclick="event.stopPropagation();toggleTask('${task.id}')" title="${task.enabled ? 'Pause' : 'Activate'}">
                        <i data-lucide="${statusIcon}" class="icon icon-sm"></i>
                    </button>
                </td>
                <td>
                    <div class="task-name">${escapeHtml(task.name)}</div>
                    ${task.remote_trigger_id ? '<small class="text-muted">RemoteTrigger</small>' : '<small class="text-muted">Local</small>'}
                </td>
                <td>
                    <code class="cron-expr">${escapeHtml(task.cron)}</code>
                    <div class="cron-desc">${escapeHtml(task.cron_human || '')}</div>
                </td>
                <td><span class="badge badge-type"><i data-lucide="${typeIcon}" class="icon icon-xs"></i> ${escapeHtml(task.type)}</span></td>
                <td>${lastRun} ${resultBadge}</td>
                <td class="actions" onclick="event.stopPropagation()">
                    <button class="btn btn-ghost btn-icon btn-sm" onclick="editTask('${task.id}')" title="Edit">
                        <i data-lucide="pencil" class="icon icon-sm"></i>
                    </button>
                    <button class="btn btn-ghost btn-icon btn-sm" onclick="deleteTask('${task.id}')" title="Delete">
                        <i data-lucide="trash-2" class="icon icon-sm"></i>
                    </button>
                </td>
            </tr>`;
    });

    tbody.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function getTypeIcon(type) {
    const icons = {
        'health-check': 'heart-pulse',
        'backup': 'shield-check',
        'issue-tracker': 'git-pull-request',
        'custom': 'terminal',
    };
    return icons[type] || 'timer';
}

// === Filter ===
function filterTasks(type) {
    currentFilter = type;
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase().includes(
            type === 'all' ? 'alle' : type.replace('-', ' ')
        ) || (type === 'all' && btn.textContent === 'Alle'));
    });
    renderTasks();
}

// === CRUD ===
function showCreateModal() {
    editingTaskId = null;
    document.getElementById('modalTitle').textContent = 'New Task';
    document.getElementById('saveBtn').textContent = 'Create';
    document.getElementById('taskName').value = '';
    document.getElementById('taskCron').value = '';
    document.getElementById('taskType').value = 'custom';
    document.getElementById('taskPrompt').value = '';
    document.getElementById('taskTriggerId').value = '';
    document.getElementById('cronPreview').textContent = '';
    openModal('taskModal');
}

function editTask(id) {
    const task = allTasks.find(t => t.id === id);
    if (!task) return;

    editingTaskId = id;
    document.getElementById('modalTitle').textContent = 'Edit Task';
    document.getElementById('saveBtn').textContent = 'Save';
    document.getElementById('taskName').value = task.name;
    document.getElementById('taskCron').value = task.cron;
    document.getElementById('taskType').value = task.type;
    document.getElementById('taskPrompt').value = task.prompt || '';
    document.getElementById('taskTriggerId').value = task.remote_trigger_id || '';
    updateCronPreview();
    openModal('taskModal');
}

function saveTask() {
    const taskData = {
        name: document.getElementById('taskName').value.trim(),
        cron: document.getElementById('taskCron').value.trim(),
        type: document.getElementById('taskType').value,
        prompt: document.getElementById('taskPrompt').value.trim(),
        remote_trigger_id: document.getElementById('taskTriggerId').value.trim() || null,
    };

    if (!taskData.name) {
        alert('Name is required');
        return;
    }
    if (!taskData.cron || taskData.cron.split(' ').length !== 5) {
        alert('Valid cron expression required (5 fields)');
        return;
    }

    const url = editingTaskId
        ? `/api/scheduled-tasks/${editingTaskId}`
        : '/api/scheduled-tasks';
    const method = editingTaskId ? 'PUT' : 'POST';

    api.request(url, {
        method,
        body: taskData,
    })
    .then(result => {
        if (result.success) {
            closeTaskModal();
            loadTasks();
        } else {
            alert(result.error || 'Error saving');
        }
    })
    .catch(err => alert('Error: ' + err.message));
}

function deleteTask(id) {
    const task = allTasks.find(t => t.id === id);
    if (!task) return;
    if (!confirm(`Really delete task "${task.name}"?`)) return;

    api.del(`/api/scheduled-tasks/${id}`)
        .then(result => {
            if (result.success) loadTasks();
            else alert(result.error || 'Error deleting');
        })
        .catch(err => alert('Error: ' + err.message));
}

function toggleTask(id) {
    api.post(`/api/scheduled-tasks/${id}/toggle`)
        .then(result => {
            if (result.success) loadTasks();
        })
        .catch(err => console.error('Toggle error:', err));
}

// === Templates ===
function createFromTemplate(type) {
    const tpl = templates[type];
    if (!tpl) {
        showCreateModal();
        document.getElementById('taskType').value = type;
        return;
    }

    editingTaskId = null;
    document.getElementById('modalTitle').textContent = 'New Task (from template)';
    document.getElementById('saveBtn').textContent = 'Create';
    document.getElementById('taskName').value = tpl.name;
    document.getElementById('taskCron').value = tpl.cron;
    document.getElementById('taskType').value = tpl.type;
    document.getElementById('taskPrompt').value = tpl.prompt;
    document.getElementById('taskTriggerId').value = '';
    updateCronPreview();
    openModal('taskModal');
}

// === Detail View ===
function showDetail(id) {
    const task = allTasks.find(t => t.id === id);
    if (!task) return;

    document.getElementById('detailTitle').textContent = task.name;

    const triggerInfo = task.remote_trigger_id
        ? `<div class="detail-field"><label>Remote Trigger ID</label><code>${escapeHtml(task.remote_trigger_id)}</code></div>`
        : '<div class="detail-field"><label>Remote Trigger</label><span class="text-muted">Not linked - task is local to dashboard only</span></div>';

    document.getElementById('detailBody').innerHTML = `
        <div class="detail-grid">
            <div class="detail-field">
                <label>Status</label>
                <span class="badge badge-${task.enabled ? 'success' : 'warning'}">${task.enabled ? 'Active' : 'Paused'}</span>
            </div>
            <div class="detail-field">
                <label>Typ</label>
                <span class="badge badge-type">${escapeHtml(task.type)}</span>
            </div>
            <div class="detail-field">
                <label>Schedule</label>
                <code>${escapeHtml(task.cron)}</code> - ${escapeHtml(task.cron_human || '')}
            </div>
            ${triggerInfo}
            <div class="detail-field">
                <label>Last Run</label>
                ${task.last_run ? formatTimeAgo(task.last_run) : '<span class="text-muted">Never</span>'}
                ${task.last_result ? ` <span class="badge badge-${task.last_result === 'ok' ? 'success' : 'error'}">${task.last_result}</span>` : ''}
            </div>
            <div class="detail-field">
                <label>Created</label>
                ${formatDate(task.created_at)}
            </div>
        </div>
        <div class="detail-prompt">
            <label>Prompt</label>
            <pre>${escapeHtml(task.prompt || 'No prompt defined')}</pre>
        </div>
        <div class="detail-info">
            <i data-lucide="info" class="icon icon-sm"></i>
            To create this task as a Claude Code RemoteTrigger, use in the CLI:<br>
            <code>RemoteTrigger create</code> with the prompt and cron expression above.
        </div>
    `;

    openModal('detailModal');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeDetailModal() {
    closeModal('detailModal');
}

// === Cron Preview ===
function updateCronPreview() {
    const cron = document.getElementById('taskCron').value.trim();
    const preview = document.getElementById('cronPreview');

    if (!cron || cron.split(' ').length !== 5) {
        preview.textContent = cron ? 'Format: Minute Hour Day Month Weekday' : '';
        return;
    }

    preview.textContent = describeCron(cron);
}

function setCron(expr) {
    document.getElementById('taskCron').value = expr;
    updateCronPreview();
}

function describeCron(expr) {
    const presets = {
        '* * * * *': 'Every minute',
        '*/5 * * * *': 'Every 5 minutes',
        '*/15 * * * *': 'Every 15 minutes',
        '*/30 * * * *': 'Every 30 minutes',
        '0 * * * *': 'Hourly',
    };
    if (presets[expr]) return presets[expr];

    const [min, hour, dom, , dow] = expr.split(' ');
    if (min.startsWith('*/')) return `Every ${min.slice(2)} minutes`;
    if (hour.startsWith('*/')) return `Every ${hour.slice(2)} hours`;

    if (min !== '*' && hour !== '*') {
        const time = `${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
        if (dow === '1-5') return `Weekdays at ${time}`;
        if (dow === '0' || dow === '7') return `Sundays at ${time}`;
        if (dom !== '*') return `On the ${dom}. at ${time}`;
        return `Daily at ${time}`;
    }
    return expr;
}

// === Modal ===
function closeTaskModal() {
    closeModal('taskModal');
    editingTaskId = null;
}
// Escape wird global in base.js gehandelt

// Auto-refresh
setInterval(loadTasks, 30000);
