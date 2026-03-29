// === DASHBOARD ACTIONS ===
// Favoriten, Archiv, Context-Menu, Info-Modal, Terminal, Refresh, Cleanup

// Favoriten laden
function loadFavorites() {
    return api.get('/api/favorites')
        .then(data => { favorites = data || []; })
        .catch(() => { favorites = []; });
}

function toggleFavorite(name, btn) {
    api.post('/api/favorites', {name: name})
    .then(data => {
        if (data.success) {
            favorites = data.favorites;
            btn.classList.toggle('active', favorites.includes(name));
            btn.innerHTML = '<i data-lucide="star" class="icon"></i>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
            // Tabelle neu rendern für Sortierung
            if (allProjectsData.projects) renderProjectsTable(allProjectsData);
        }
    });
}

function toggleArchive(name, archived) {
    closeAllCtx();
    api.post('/api/project/' + encodeURIComponent(name) + '/archive', {archived: archived})
    .then(data => {
        if (data.success) {
            // Daten neu laden
            loadData();
        }
    });
}

function toggleShowArchived() {
    showArchived = !showArchived;
    const btn = document.getElementById('archiveToggle');
    if (btn) {
        btn.classList.toggle('active', showArchived);
        btn.innerHTML = showArchived ? '<i data-lucide="package" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Hide Archive' : '<i data-lucide="package" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Show Archive';
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }
    applyFiltersAndSort();
}

// Row-Context-Menu
function openRowCtx(e, name) {
    e.stopPropagation();
    closeAllCtx();
    var menu = e.target.closest('.row-ctx').querySelector('.row-ctx-menu');
    if (menu) menu.classList.add('show');
}
function closeAllCtx() {
    document.querySelectorAll('.row-ctx-menu.show').forEach(function(m) { m.classList.remove('show'); });
}
document.addEventListener('click', closeAllCtx);

function showInfo(type, name) {
    document.getElementById('modalTitle').textContent = name;
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Loading description...';
    openModal('infoModal');

    api.get(`/api/info?type=${type}&name=${encodeURIComponent(name)}`)
        .then(data => {
            let html = '<div>' + data.description.replace(/\\n/g, '<br>') + '</div>';
            if (data.source) {
                html += `<div class="modal-source">Source: ${data.source}</div>`;
            }
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Error loading: ' + err;
        });
}

function closeInfoModal() {
    closeModal('infoModal');
}

function openTerminal(projectName) {
    api.get(`/api/terminal?project=${encodeURIComponent(projectName)}`)
        .then(data => {
            if (data.success) {
                alert('Terminal opened for: ' + projectName);
            } else {
                alert('Error: ' + data.error);
            }
        });
}

function refreshDescriptions() {
    document.getElementById('modalTitle').textContent = 'Update Descriptions';
    document.getElementById('modalBody').innerHTML = `
        <p>Choose how project descriptions should be updated:</p>
        <div style="margin:20px 0;display:flex;flex-direction:column;gap:10px">
            <button class="btn" onclick="executeRefresh(false)" style="padding:15px">
                <strong>Fill missing only</strong><br>
                <small style="color:#aaa">Descriptions are only generated for projects without a description</small>
            </button>
            <button class="btn" onclick="executeRefresh(true)" style="padding:15px;background:#8b4513">
                <strong>Re-detect all</strong><br>
                <small style="color:#aaa">All descriptions will be re-extracted from their sources</small>
            </button>
        </div>
        <button class="btn-cancel" onclick="closeInfoModal()" style="margin-top:10px">Cancel</button>
    `;
    openModal('infoModal');
}

function executeRefresh(forceAll) {
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Scanning projects...';

    const url = forceAll ? '/api/projects/refresh?force_descriptions=true' : '/api/projects/refresh';
    api.post(url)
        .then(data => {
            let html = `<h3>${data.updated} projects updated</h3>`;
            if (data.force_descriptions) {
                html += '<p style="color:#ffaa00">All descriptions have been re-detected.</p>';
            }
            if (data.projects && data.projects.length > 0) {
                html += '<div style="max-height:300px;overflow-y:auto;margin:15px 0">';
                html += '<table style="width:100%;font-size:13px">';
                data.projects.slice(0, 20).forEach(p => {
                    html += `<tr><td style="padding:5px;color:#4dabf7">${p.name}</td><td style="padding:5px;color:#aaa">${p.description || '-'}</td></tr>`;
                });
                if (data.projects.length > 20) {
                    html += `<tr><td colspan="2" style="padding:5px;color:#666">... and ${data.projects.length - 20} more</td></tr>`;
                }
                html += '</table></div>';
            }
            if (data.errors && data.errors.length > 0) {
                html += `<p style="color:#ff6666">${data.errors.length} error(s) occurred</p>`;
            }
            html += '<button class="btn" onclick="closeInfoModal();loadData()" style="margin-top:15px">Close & Refresh</button>';
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Error: ' + err;
        });
}

function cleanupDocker() {
    document.getElementById('modalTitle').textContent = 'Docker Cleanup';
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Analyzing...';
    openModal('infoModal');

    // Erst Analyse anzeigen
    api.get('/api/cleanup?mode=analyze')
        .then(data => {
            let html = '<h3>Analysis before cleanup:</h3><pre>' + data.result + '</pre>';
            html += '<p><a href="/api/cleanup/report?type=pre" target="_blank" class="action-link"><i data-lucide="download" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Export analysis as .md</a></p>';
            html += '<hr style="border-color:#444;margin:20px 0">';
            html += '<p>Do you want to run the cleanup?</p>';
            html += '<button class="btn" onclick="executeCleanup()" style="margin-right:10px"><i data-lucide="check" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Yes, clean up</button>';
            html += '<button class="btn" onclick="closeInfoModal()" style="background:#666"><i data-lucide="x" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Cancel</button>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Error: ' + err;
        });
}

function executeCleanup() {
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Cleaning up...';

    api.get('/api/cleanup?mode=execute')
        .then(data => {
            let html = '<h3>Cleanup completed:</h3><pre>' + data.result + '</pre>';
            if (data.space_freed) {
                html += '<p><strong>Space freed:</strong> ' + data.space_freed + '</p>';
            }
            html += '<p><a href="/api/cleanup/report?type=post" target="_blank" class="action-link"><i data-lucide="download" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Export report as .md</a></p>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
            document.getElementById('modalBody').innerHTML = html;
            loadData();
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Error: ' + err;
        });
}
