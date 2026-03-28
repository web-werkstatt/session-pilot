let allNews = [];
let currentFilter = 'all';

function loadNews() {
    api.get('/api/news')
        .then(data => {
            allNews = data.news;
            document.getElementById('timestamp').textContent = 'Stand: ' + data.timestamp;

            // Stats
            document.getElementById('totalNews').textContent = data.total;
            document.getElementById('commitCount').textContent =
                allNews.filter(n => n.type === 'commit').length;
            document.getElementById('changeCount').textContent =
                allNews.filter(n => n.type === 'file_change').length;
            document.getElementById('newProjectCount').textContent =
                allNews.filter(n => n.type === 'new_project').length;
            document.getElementById('warningCount').textContent =
                allNews.filter(n => n.type === 'sync_warning').length;

            document.getElementById('loading').style.display = 'none';

            if (allNews.length === 0) {
                document.getElementById('emptyState').style.display = 'block';
            } else {
                document.getElementById('newsTable').style.display = 'table';
                renderNews(allNews);
            }
        })
        .catch(err => {
            document.getElementById('loading').innerHTML =
                '<div style="color:#e74c3c;">Fehler: ' + err + '</div>';
        });
}

function filterNews(type) {
    currentFilter = type;
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');

    const filtered = type === 'all'
        ? allNews
        : allNews.filter(n => n.type === type);

    if (filtered.length === 0) {
        document.getElementById('newsTable').style.display = 'none';
        document.getElementById('emptyState').style.display = 'block';
    } else {
        document.getElementById('newsTable').style.display = 'table';
        document.getElementById('emptyState').style.display = 'none';
        renderNews(filtered);
    }
}

function renderNews(news) {
    const tbody = document.getElementById('newsTableBody');

    const icons = {
        'commit': '<i data-lucide="file-text" class="icon"></i>',
        'file_change': '<i data-lucide="file" class="icon"></i>',
        'new_project': '<i data-lucide="plus-circle" class="icon"></i>',
        'sync_warning': '<i data-lucide="alert-triangle" class="icon"></i>'
    };

    const typeLabels = {
        'commit': 'Commit',
        'file_change': 'Änderung',
        'new_project': 'Neu',
        'sync_warning': 'Warnung'
    };

    let html = '';
    news.forEach(item => {
        const icon = icons[item.type] || '<i data-lucide="pin" class="icon"></i>';
        const typeLabel = typeLabels[item.type] || item.type;
        const daysAgoText = item.days_ago === 0 ? 'Heute' :
            item.days_ago === 1 ? 'Gestern' : `Vor ${item.days_ago} Tagen`;

        html += `
            <tr class="type-${item.type} clickable" onclick="showDetail('${item.project}', '${item.type}')">
                <td class="news-icon">${icon}</td>
                <td class="project-name">${item.project}</td>
                <td class="news-message">${item.message || item.title}</td>
                <td><span class="badge badge-${item.type}">${typeLabel}</span></td>
                <td class="date-cell">
                    ${item.date}
                    <span class="days-ago">${daysAgoText}</span>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

// === MODAL FUNKTIONEN ===
function showDetail(project, type) {
    const detailIcons = {
        'commit': '<i data-lucide="file-text" class="icon"></i>',
        'file_change': '<i data-lucide="file" class="icon"></i>',
        'new_project': '<i data-lucide="plus-circle" class="icon"></i>',
        'sync_warning': '<i data-lucide="alert-triangle" class="icon"></i>'
    };
    document.getElementById('modalIcon').innerHTML = detailIcons[type] || '<i data-lucide="pin" class="icon"></i>';
    document.getElementById('modalProject').textContent = project;
    document.getElementById('modalBody').innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <div>Lade Details...</div>
        </div>
    `;
    openModal('detailModal');
    if (typeof lucide !== 'undefined') lucide.createIcons();

    api.get(`/api/news/detail/${encodeURIComponent(project)}`)
        .then(data => {
            renderDetail(data, type);
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = `
                <div style="color:#e74c3c;text-align:center;padding:30px;">
                    Fehler beim Laden: ${err}
                </div>
            `;
        });
}

function renderDetail(data, newsType) {
    const body = document.getElementById('modalBody');
    let html = '';

    // Projekt-Info
    const info = data.project_info || {};
    html += `
        <div class="detail-section">
            <h3><i data-lucide="clipboard-list" class="icon"></i> Projekt-Info</h3>
            <div class="detail-card">
                <div class="detail-row">
                    <span class="detail-label">Name</span>
                    <span class="detail-value">${data.project}</span>
                </div>
                ${info.description ? `
                <div class="detail-row">
                    <span class="detail-label">Beschreibung</span>
                    <span class="detail-value">${info.description}</span>
                </div>` : ''}
                ${info.category ? `
                <div class="detail-row">
                    <span class="detail-label">Kategorie</span>
                    <span class="detail-value">${info.category}</span>
                </div>` : ''}
                ${info.status ? `
                <div class="detail-row">
                    <span class="detail-label">Status</span>
                    <span class="detail-value">${info.status}</span>
                </div>` : ''}
            </div>
            ${info.tags && info.tags.length > 0 ? `
            <div class="tag-list" style="margin-top:12px;">
                ${info.tags.map(t => `<span class="tag">${t}</span>`).join('')}
            </div>` : ''}
        </div>
    `;

    // Git Status
    if (data.git_status) {
        const gs = data.git_status;
        html += `
            <div class="detail-section">
                <h3><i data-lucide="git-branch" class="icon"></i> Git Status</h3>
                <div class="git-status-grid">
                    <div class="git-stat">
                        <div class="git-stat-value ${gs.clean ? 'git-clean' : 'git-dirty'}">
                            ${gs.clean ? '<i data-lucide="check" class="icon"></i>' : gs.changes}
                        </div>
                        <div class="git-stat-label">${gs.clean ? 'Sauber' : 'Änderungen'}</div>
                    </div>
                    <div class="git-stat">
                        <div class="git-stat-value" style="color:#f39c12">${gs.modified}</div>
                        <div class="git-stat-label">Modifiziert</div>
                    </div>
                    <div class="git-stat">
                        <div class="git-stat-value" style="color:#3498db">${gs.staged}</div>
                        <div class="git-stat-label">Staged</div>
                    </div>
                    <div class="git-stat">
                        <div class="git-stat-value" style="color:#9b59b6">${gs.untracked}</div>
                        <div class="git-stat-label">Untracked</div>
                    </div>
                </div>
            </div>
        `;
    }

    // Commits
    if (data.commits && data.commits.length > 0) {
        html += `
            <div class="detail-section">
                <h3><i data-lucide="file-text" class="icon"></i> Letzte Commits</h3>
                ${data.commits.map(c => `
                    <div class="commit-item">
                        <span class="commit-sha">${c.sha}</span>
                        <div class="commit-msg">${escapeHtml(c.message)}</div>
                        <div class="commit-meta">${c.author} • ${c.when}</div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // Kürzlich geänderte Dateien
    if (data.recent_files && data.recent_files.length > 0) {
        html += `
            <div class="detail-section">
                <h3><i data-lucide="file" class="icon"></i> Kürzlich geänderte Dateien</h3>
                ${data.recent_files.map(f => `
                    <div class="file-item">
                        <span class="file-name">${escapeHtml(f.name)}</span>
                        <span class="file-time">${f.modified}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // Pfad
    html += `
        <div class="detail-section" style="margin-bottom:0">
            <h3><i data-lucide="folder-open" class="icon"></i> Pfad</h3>
            <div class="detail-card" style="font-family:monospace;font-size:13px;color:#888;">
                ${data.path}
            </div>
        </div>
    `;

    body.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeNewsModal() {
    closeModal('detailModal');
}
// Escape wird global in base.js gehandelt

// Laden
loadNews();
// Auto-Refresh alle 30 Sekunden (still)
setInterval(loadNews, 30000);
