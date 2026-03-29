/**
 * Git-Aktionen Panel fuer Projekt-Detailseite
 * Wird nach loadProjectInfo() aufgerufen
 */

let gitProjectName = '';

function initGitPanel(projectName) {
    gitProjectName = projectName;
    loadGitStatus();
}

function loadGitStatus(doFetch) {
    var url = '/api/git/' + encodeURIComponent(gitProjectName) + '/status';
    if (doFetch) url += '?fetch=1';
    api.get(url)
        .then(renderGitPanel)
        .catch(() => {
            const el = document.getElementById('gitPanel');
            if (el) el.innerHTML = '<span style="color:#555;font-size:12px">Git not available</span>';
        });
}

function renderGitPanel(data) {
    const panel = document.getElementById('gitPanel');
    if (!panel) return;

    if (!data.is_git) {
        panel.innerHTML = '<span style="color:#555;font-size:12px">Not a git repository</span>';
        return;
    }

    const changeCount = data.changes.length;
    const statusColor = changeCount > 0 ? '#ffaa00' : '#4caf50';
    const statusText = changeCount > 0 ? changeCount + ' change' + (changeCount > 1 ? 's' : '') : 'Clean';

    let syncInfo = '';
    if (data.has_remote) {
        if (data.ahead > 0 && data.behind > 0) {
            syncInfo = `<span style="color:#ff9800">${data.ahead} ahead, ${data.behind} behind</span>`;
        } else if (data.ahead > 0) {
            syncInfo = `<span style="color:#5b9bd5">${data.ahead} commit${data.ahead > 1 ? 's' : ''} ahead</span>`;
        } else if (data.behind > 0) {
            syncInfo = `<span style="color:#ff9800">${data.behind} commit${data.behind > 1 ? 's' : ''} behind</span>`;
        } else {
            syncInfo = '<span style="color:#4caf50">Up to date</span>';
        }
    }

    let html = `
        <div class="git-header">
            <span class="git-branch">${data.branch || 'HEAD'}</span>
            <span class="git-status" style="color:${statusColor}">${statusText}</span>
            ${syncInfo ? '<span class="git-sync">' + syncInfo + '</span>' : ''}
            <button class="git-btn refresh" onclick="loadGitStatus(true)" title="Refresh (with fetch)">&#8635;</button>
        </div>`;

    // Changed files
    if (changeCount > 0) {
        html += '<div style="display:flex;gap:12px;font-size:10px;color:#666;margin-bottom:6px">';
        html += '<span><span style="color:#ffaa00;font-weight:700">M</span> Modified</span>';
        html += '<span><span style="color:#4caf50;font-weight:700">A</span> Added</span>';
        html += '<span><span style="color:#ef5350;font-weight:700">D</span> Deleted</span>';
        html += '<span><span style="color:#888;font-weight:700">?</span> Untracked</span>';
        html += '</div>';
        html += '<div class="git-changes">';
        const shown = data.changes.slice(0, 15);
        shown.forEach(c => {
            const icon = c.status === 'M' ? 'M' : c.status === 'A' ? 'A' : c.status === 'D' ? 'D' : c.status === '??' ? '?' : c.status;
            const color = c.status === 'D' ? '#ef5350' : c.status === 'A' ? '#4caf50' : c.status === '??' ? '#888' : '#ffaa00';
            html += `<div class="git-change"><span class="git-change-status" style="color:${color}">${icon}</span><span class="git-change-file">${c.file}</span></div>`;
        });
        if (data.changes.length > 15) {
            html += `<div class="git-change" style="color:#555">... and ${data.changes.length - 15} more</div>`;
        }
        html += '</div>';

        // Commit form
        html += `
        <div class="git-commit-form">
            <input type="text" id="gitCommitMsg" class="git-commit-input" placeholder="Commit message..." onkeydown="if(event.key==='Enter')doGitCommit()">
            <button class="git-btn commit" onclick="doGitCommit()">Commit</button>
        </div>`;
    }

    // Aktions-Buttons
    html += '<div class="git-actions">';
    if (data.has_remote) {
        if (data.ahead > 0) {
            html += `<button class="git-btn push" onclick="doGitPush()">Push (${data.ahead})</button>`;
        }
        if (data.behind > 0) {
            html += `<button class="git-btn pull" onclick="doGitPull()">Pull (${data.behind})</button>`;
        }
        if (data.ahead === 0 && data.behind === 0 && changeCount === 0) {
            html += '<span style="color:#555;font-size:11px">All up to date</span>';
        }
    } else {
        html += '<span style="color:#555;font-size:11px">No remote configured</span>';
    }
    html += '</div>';

    panel.innerHTML = html;
}

function doGitCommit() {
    const input = document.getElementById('gitCommitMsg');
    const msg = input.value.trim();
    if (!msg) { input.focus(); return; }

    input.disabled = true;
    api.post('/api/git/' + encodeURIComponent(gitProjectName) + '/commit', {message: msg})
    .then(data => {
        input.disabled = false;
        if (data.success) {
            input.value = '';
            showGitToast('Commit successful', 'success');
            loadGitStatus();
        } else {
            showGitToast(data.error || data.output || 'Error', 'error');
        }
    })
    .catch(() => { input.disabled = false; showGitToast('Network error', 'error'); });
}

function doGitPush() {
    showGitToast('Pushing...', 'success');
    api.post('/api/git/' + encodeURIComponent(gitProjectName) + '/push')
        .then(data => {
            showGitToast(data.success ? 'Push successful' : (data.error || data.output), data.success ? 'success' : 'error');
            if (data.success) loadGitStatus();
        })
        .catch(() => showGitToast('Network error', 'error'));
}

function doGitPull() {
    showGitToast('Pulling...', 'success');
    api.post('/api/git/' + encodeURIComponent(gitProjectName) + '/pull')
        .then(data => {
            showGitToast(data.success ? 'Pull successful' : (data.error || data.output), data.success ? 'success' : 'error');
            if (data.success) loadGitStatus();
        })
        .catch(() => showGitToast('Network error', 'error'));
}

function showGitToast(msg, type) {
    // Verwende existierenden Toast oder erstelle temporaeren
    let t = document.getElementById('gitToast');
    if (!t) {
        t = document.createElement('div');
        t.id = 'gitToast';
        t.style.cssText = 'position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:8px;font-size:13px;z-index:2000;opacity:0;transition:opacity 0.3s;pointer-events:none;';
        document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.background = type === 'success' ? '#1b5e20' : '#b71c1c';
    t.style.color = type === 'success' ? '#a5d6a7' : '#ef9a9a';
    t.style.border = '1px solid ' + (type === 'success' ? '#2e7d32' : '#c62828');
    t.style.opacity = '1';
    setTimeout(() => { t.style.opacity = '0'; }, 3000);
}
