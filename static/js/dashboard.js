let firstLoad = true;
let allRelations = [];
let relationTypes = [];
let groupsData = { groups: [] };
let favorites = [];
let showArchived = false;

// Favoriten laden
function loadFavorites() {
    return fetch('/api/favorites')
        .then(r => r.json())
        .then(data => { favorites = data || []; })
        .catch(() => { favorites = []; });
}

function toggleFavorite(name, btn) {
    fetch('/api/favorites', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            favorites = data.favorites;
            btn.classList.toggle('active', favorites.includes(name));
            btn.textContent = favorites.includes(name) ? '★' : '☆';
            // Tabelle neu rendern für Sortierung
            if (allProjectsData.projects) renderProjectsTable(allProjectsData);
        }
    });
}

function toggleArchive(name, archived) {
    closeAllCtx();
    fetch('/api/project/' + encodeURIComponent(name) + '/archive', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({archived: archived})
    })
    .then(r => r.json())
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
        btn.textContent = showArchived ? '📦 Archiv ausblenden' : '📦 Archiv anzeigen';
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

// Gruppen laden
function loadGroups() {
    return fetch('/api/groups')
        .then(r => r.json())
        .then(data => {
            groupsData = data;
            renderGroupFilterButtons();
            return data;
        })
        .catch(err => {
            console.error('Fehler beim Laden der Gruppen:', err);
            return { groups: [] };
        });
}

// Gruppen-Filter-Buttons dynamisch rendern
function renderGroupFilterButtons() {
    const container = document.getElementById('groupFilterButtons');
    let html = '<button class="filter-btn active" onclick="setGroupFilter(\'all\')">Alle</button>';

    groupsData.groups.forEach(group => {
        html += `<button class="filter-btn" onclick="setGroupFilter('${group.id}')">${group.icon} ${group.name}</button>`;
    });

    container.innerHTML = html;
}

// Gruppen-Dropdown im Edit-Modal aktualisieren
function updateGroupDropdown(selectNewGroupId = null) {
    const select = document.getElementById('editGroup');
    const currentValue = select.value;
    let html = '<option value="">-- Keine --</option>';

    groupsData.groups.forEach(group => {
        html += `<option value="${group.id}">${group.icon} ${group.name}</option>`;
    });

    select.innerHTML = html;

    // Entweder neue Gruppe oder vorherigen Wert wiederherstellen
    if (selectNewGroupId) {
        select.value = selectNewGroupId;
    } else if (currentValue) {
        select.value = currentValue;
    }
}

// Inline-Formular für neue Gruppe ein-/ausblenden
function toggleInlineGroupForm() {
    const form = document.getElementById('inlineGroupForm');
    if (form.style.display === 'none') {
        form.style.display = 'block';
        document.getElementById('inlineGroupId').focus();
    } else {
        form.style.display = 'none';
        // Felder zurücksetzen
        document.getElementById('inlineGroupId').value = '';
        document.getElementById('inlineGroupName').value = '';
        document.getElementById('inlineGroupIcon').value = '📁';
        document.getElementById('inlineGroupColor').value = '#666666';
    }
}

// Neue Gruppe inline erstellen
function createInlineGroup() {
    let id = document.getElementById('inlineGroupId').value.trim().toLowerCase();
    id = id.replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    const name = document.getElementById('inlineGroupName').value.trim();
    const icon = document.getElementById('inlineGroupIcon').value;
    const color = document.getElementById('inlineGroupColor').value;

    if (!id || !name) {
        alert('Kurzname und Anzeigename sind erforderlich');
        return;
    }

    fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, icon, color, description: '' })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            // Gruppen neu laden und neue Gruppe auswählen
            loadGroups().then(() => {
                updateGroupDropdown(id);
                toggleInlineGroupForm();
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// Gruppen-Badge dynamisch generieren
function getGroupBadge(groupId) {
    if (!groupId) return '-';
    const group = groupsData.groups.find(g => g.id === groupId);
    if (group) {
        return `<span title="${group.name}" style="font-size:16px">${group.icon}</span>`;
    }
    return '-';
}

// Gruppen-Modal öffnen
function openGroupsModal() {
    document.getElementById('groupsModal').classList.add('show');
    renderGroupsList();
}

function closeGroupsModal() {
    document.getElementById('groupsModal').classList.remove('show');
}

// Gruppen-Liste im Modal rendern
function renderGroupsList() {
    const container = document.getElementById('groupsList');

    if (groupsData.groups.length === 0) {
        container.innerHTML = '<p style="color:#888;text-align:center">Keine Gruppen definiert</p>';
        return;
    }

    let html = '';
    groupsData.groups.forEach(group => {
        html += `
            <div class="group-item" data-group-id="${group.id}">
                <div class="group-color-bar" style="background:${group.color}"></div>
                <div class="group-icon-preview">${group.icon}</div>
                <div class="group-info">
                    <div class="group-name">${group.name}</div>
                    <div class="group-id">${group.id}</div>
                    ${group.description ? `<div class="group-desc">${group.description}</div>` : ''}
                </div>
                <div class="group-actions">
                    <button onclick="editGroup('${group.id}')">Bearbeiten</button>
                    <button class="btn-delete" onclick="deleteGroup('${group.id}')">Löschen</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Neue Gruppe erstellen
function createGroup() {
    // ID bereinigen: Kleinbuchstaben, Leerzeichen durch Unterstriche ersetzen, Sonderzeichen entfernen
    let id = document.getElementById('newGroupId').value.trim().toLowerCase();
    id = id.replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    const name = document.getElementById('newGroupName').value.trim();
    const icon = document.getElementById('newGroupIcon').value.trim() || '📁';
    const color = document.getElementById('newGroupColor').value;
    const desc = document.getElementById('newGroupDesc').value.trim();

    if (!id || !name) {
        alert('ID und Name sind erforderlich');
        return;
    }

    fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, icon, color, description: desc })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            // Felder leeren
            document.getElementById('newGroupId').value = '';
            document.getElementById('newGroupName').value = '';
            document.getElementById('newGroupIcon').value = '';
            document.getElementById('newGroupColor').value = '#666666';
            document.getElementById('newGroupDesc').value = '';
            // Gruppen neu laden
            loadGroups().then(() => {
                renderGroupsList();
                updateGroupDropdown();
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// Gruppe bearbeiten
function editGroup(groupId) {
    const group = groupsData.groups.find(g => g.id === groupId);
    if (!group) return;

    const newName = prompt('Name:', group.name);
    if (newName === null) return;

    const newIcon = prompt('Icon (Emoji):', group.icon);
    if (newIcon === null) return;

    const newColor = prompt('Farbe (Hex):', group.color);
    if (newColor === null) return;

    const newDesc = prompt('Beschreibung:', group.description || '');
    if (newDesc === null) return;

    fetch(`/api/groups/${groupId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: newName,
            icon: newIcon,
            color: newColor,
            description: newDesc
        })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            loadGroups().then(() => {
                renderGroupsList();
                updateGroupDropdown();
                loadData(); // Tabelle aktualisieren
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// Gruppe löschen
function deleteGroup(groupId) {
    const group = groupsData.groups.find(g => g.id === groupId);
    if (!group) return;

    if (!confirm(`Möchten Sie die Gruppe "${group.name}" wirklich löschen?\n\nProjekte mit dieser Gruppe werden auf "Keine Gruppe" gesetzt.`)) {
        return;
    }

    fetch(`/api/groups/${groupId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            loadGroups().then(() => {
                renderGroupsList();
                updateGroupDropdown();
                loadData(); // Tabelle aktualisieren
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// News Ticker laden - mit sanftem Update ohne Ruckeln
let currentNewsHash = '';

function loadNews() {
    fetch('/api/news')
        .then(r => r.json())
        .then(data => {
            // Nur aktualisieren wenn sich etwas geändert hat
            const newHash = JSON.stringify(data.headlines.map(h => h.project + h.type));
            if (newHash !== currentNewsHash) {
                currentNewsHash = newHash;
                renderNewsTicker(data.headlines);
            }
        })
        .catch(err => console.error('News laden fehlgeschlagen:', err));
}

function renderNewsTicker(headlines) {
    const container = document.getElementById('newsTickerContent');
    if (!headlines || headlines.length === 0) {
        if (container.innerHTML.includes('Lade')) {
            container.innerHTML = '<span class="news-item">Keine aktuellen Neuigkeiten</span>';
        }
        return;
    }

    // Icons für verschiedene News-Typen
    const icons = {
        'commit': '📝',
        'file_change': '📄',
        'new_project': '🆕',
        'sync_warning': '⚠️'
    };

    // Erstelle News-Items (doppelt für endlose Animation)
    let html = '';
    const items = [...headlines, ...headlines]; // Verdoppeln für nahtlose Animation
    items.forEach(news => {
        const icon = icons[news.type] || '📌';
        html += `
            <span class="news-item" onclick="window.location='/news'">
                <span class="news-icon">${icon}</span>
                <span class="news-project">${news.project}</span>
                <span class="news-message">${news.message || news.title}</span>
            </span>
        `;
    });

    // Sanftes Update: Animation kurz pausieren
    container.style.animationPlayState = 'paused';
    container.innerHTML = html;
    // Animation nach kleinem Delay fortsetzen
    requestAnimationFrame(() => {
        container.style.animationPlayState = 'running';
    });
}

function loadData() {
    // Nur beim ersten Laden den Spinner zeigen
    if (firstLoad) {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('projectTable').style.display = 'none';
    }

    // Daten und Relations parallel laden
    Promise.all([
        fetch('/api/data').then(r => r.json()),
        fetch('/api/relations').then(r => r.json())
    ])
        .then(([data, relationsData]) => {
            allRelations = relationsData.relations || [];
            if (relationTypes.length === 0 && relationsData.relation_types) {
                relationTypes = relationsData.relation_types;
            }
            renderData(data);
            // Spinner ausblenden sobald Daten da (egal ob firstLoad)
            var loadEl = document.getElementById('loading');
            if (loadEl && loadEl.style.display !== 'none') {
                loadEl.style.display = 'none';
                document.getElementById('projectTable').style.display = 'table';
            }
            if (firstLoad) {
                firstLoad = false;
                loadNews();
            }
        })
        .catch(err => {
            console.error('Laden fehlgeschlagen:', err);
            if (firstLoad) {
                setTimeout(loadData, 2000);
            }
        });
}

// Tab-Funktion
function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabName + 'Tab').classList.add('active');
    event.target.classList.add('active');
    if (tabName === 'widgets' && !window._widgetsLoaded) {
        loadWidgets();
    }
}

function renderData(data) {
    // Stats
    document.getElementById('totalProjects').textContent = data.stats.total_projects;
    document.getElementById('totalContainers').textContent = data.stats.total_containers;
    document.getElementById('runningContainers').textContent = data.stats.running;
    document.getElementById('unhealthyContainers').textContent = data.stats.unhealthy;
    document.getElementById('stoppedContainers').textContent = data.stats.stopped;
    document.getElementById('giteaRepos').textContent = data.stats.gitea_repos || 0;
    document.getElementById('timestamp').textContent = 'Stand: ' + data.timestamp;

    // Gitea Tabelle rendern
    const giteaBody = document.getElementById('giteaTableBody');
    giteaBody.innerHTML = '';
    if (data.gitea_repos && data.gitea_repos.length > 0) {
        data.gitea_repos.forEach(repo => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="project-name">${repo.name}</td>
                <td class="project-function">${repo.description || '-'}</td>
                <td>${repo.updated_at || '-'}</td>
                <td>${repo.open_issues > 0 ? '<span style="color:#ff9800">' + repo.open_issues + '</span>' : '0'}</td>
                <td><a href="${repo.html_url}" target="_blank" class="action-link">Öffnen</a></td>
            `;
            giteaBody.appendChild(tr);
        });
    } else {
        giteaBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#888">Keine Gitea-Repos gefunden</td></tr>';
    }

    // New projects bar mit Konfetti!
    const newBar = document.getElementById('newProjectsBar');
    if (data.new_projects.length > 0) {
        newBar.textContent = '🆕 ' + data.new_projects.length + ' neue Projekte: ' + data.new_projects.slice(0,5).join(', ') + (data.new_projects.length > 5 ? '...' : '');
        newBar.classList.add('show');
        launchConfetti();
    } else {
        newBar.classList.remove('show');
    }

    // Daten speichern für View-Mode Wechsel
    allProjectsData = data;

    // Tabelle rendern
    renderProjectsTable(data);
}

// === GLOBALE HELPER-FUNKTIONEN FÜR TABELLEN-RENDERING ===

function getPriorityBadge(priority) {
    if (priority === 'high') return '<span class="priority-high">🔴</span>';
    if (priority === 'medium') return '<span class="priority-medium">🟡</span>';
    if (priority === 'low') return '<span class="priority-low">🟢</span>';
    return '-';
}

function getDeadlineBadge(deadline) {
    if (!deadline) return '-';
    const today = new Date();
    const dl = new Date(deadline);
    const days = Math.ceil((dl - today) / (1000 * 60 * 60 * 24));
    const parts = deadline.split('-');
    const formatted = parts[2] + '.' + parts[1] + '.' + parts[0].substring(2);
    if (days < 0) return `<span class="deadline-urgent" style="white-space:nowrap">⚠️ ${formatted}</span>`;
    if (days <= 7) return `<span class="deadline-urgent" style="white-space:nowrap">${formatted}</span>`;
    if (days <= 30) return `<span class="deadline-soon" style="white-space:nowrap">${formatted}</span>`;
    return `<span class="deadline-ok" style="white-space:nowrap">${formatted}</span>`;
}

function getProgressBar(progress) {
    if (progress === null || progress === undefined) return '-';
    return `<div class="progress-bar"><div class="progress-fill" style="width:${progress}%"></div></div><span class="progress-text">${progress}%</span>`;
}

function getMilestones(milestones) {
    if (!milestones || milestones.length === 0) return '-';
    return milestones.map(m =>
        m.done ? `<span class="milestone milestone-done">✓${m.name}</span>`
               : `<span class="milestone milestone-pending">○${m.name}</span>`
    ).join('');
}

function getRelationBadges(projectName) {
    const outgoing = allRelations.filter(r => r.source === projectName);
    const incoming = allRelations.filter(r => r.target === projectName);
    const total = outgoing.length + incoming.length;

    if (total === 0) return '';

    let badges = '';

    outgoing.forEach(rel => {
        const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: '🔗', color: '#888'};
        badges += `<span class="relation-badge" style="background:${typeInfo.color}" title="${typeInfo.icon} → ${rel.target}${rel.note ? ': ' + rel.note : ''}">${typeInfo.icon}</span>`;
    });

    incoming.forEach(rel => {
        const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: '🔗', color: '#888'};
        badges += `<span class="relation-badge incoming" style="background:${typeInfo.color}" title="${typeInfo.icon} ← ${rel.source}${rel.note ? ': ' + rel.note : ''}">${typeInfo.icon}</span>`;
    });

    return `<span class="relation-badges">${badges}</span>`;
}

function renderProject(proj, isNew) {
    const tr = document.createElement('tr');
    tr.dataset.group = proj.group || '';
    tr.dataset.priority = proj.priority || '';
    tr.dataset.projecttype = proj.project_type || 'project';
    tr.dataset.parent = proj.parent_project || '';
    tr.dataset.archived = proj.archived ? '1' : '';
    if (proj.archived) tr.style.opacity = '0.45';

    // Suchbarer Text: Name + Beschreibung + Tags + Parent
    tr.dataset.searchtext = [
        proj.name,
        proj.display_name || '',
        proj.function || '',
        proj.description || '',
        proj.parent_project || '',
        (proj.tags || []).join(' ')
    ].join(' ').toLowerCase();

    if (isNew) tr.classList.add('new-project');

    // Sub-Projekt Styling
    const isSubproject = proj.project_type === 'subproject';
    if (isSubproject) {
        tr.classList.add('subproject-row');
    }

    // Git Badge (kompakt)
    let gitBadge = '';
    if (proj.sync_status === 'synced') gitBadge = '<span class="badge" style="background:#0066cc;font-size:10px">✓</span>';
    else if (proj.sync_status === 'differs') gitBadge = '<span class="badge" style="background:#cc3300;font-size:10px">⚠</span>';
    else if (proj.git_status === 'geändert') gitBadge = '<span class="badge" style="background:#8b4513;font-size:10px">M</span>';
    else if (proj.git_status === 'sauber') gitBadge = '<span class="badge" style="background:#2d5a2d;font-size:10px">✓</span>';

    // Letzte Aktivität
    let lastActivity = '-';
    if (proj.last_commit && proj.last_file_change) {
        lastActivity = proj.last_commit > proj.last_file_change ? proj.last_commit : proj.last_file_change;
    } else {
        lastActivity = proj.last_file_change || proj.last_commit || '-';
    }
    if (lastActivity !== '-') {
        var d = lastActivity.substring(0, 10).split('-');
        lastActivity = d[2] + '.' + d[1] + '.' + d[0].substring(2);
    }

    // Projekt-Name mit Sub-Projekt Formatierung
    let displayName = proj.name;
    let namePrefix = '';
    if (isSubproject) {
        namePrefix = '<span class="subproject-indicator">↳</span>';
        displayName = proj.display_name || proj.name.split('/').pop();
    }

    // Typ-Badge für Monorepos und Sub-Projekte
    let typeBadge = '';
    if (proj.project_type === 'monorepo') {
        typeBadge = '<span class="badge" style="background:#6b5b95;font-size:9px;margin-left:5px">MONO</span>';
    } else if (isSubproject) {
        const typeLabels = {app:'APP', package:'PKG', service:'SVC', module:'MOD', library:'LIB', plugin:'PLG', theme:'THM', site:'SITE'};
        const typeLabel = typeLabels[proj.category] || 'SUB';
        typeBadge = `<span class="badge" style="background:#555;font-size:9px;margin-left:5px">${typeLabel}</span>`;
    }

    const isFav = favorites.includes(proj.name);
    const favBtn = `<button class="fav-btn ${isFav ? 'active' : ''}" onclick="event.stopPropagation();toggleFavorite('${proj.name}',this)" title="Favorit">${isFav ? '★' : '☆'}</button>`;
    const projInfoIcon = `<span class="info-icon" onclick="event.stopPropagation();location.href='/project/${encodeURIComponent(proj.name)}'" title="Details">ℹ️</span>`;

    const relationBadges = getRelationBadges(proj.name);

    // Escaped name for JS strings
    const eName = proj.name.replace(/'/g, "\\'");

    const ctxMenu = `<div class="row-ctx">
        <button class="row-ctx-btn" onclick="openRowCtx(event,'${eName}')" title="Aktionen">⋯</button>
        <div class="row-ctx-menu">
            <div class="row-ctx-item" onclick="event.stopPropagation();location.href='/project/${encodeURIComponent(eName)}'">ℹ️ Details</div>
            <div class="row-ctx-item" onclick="event.stopPropagation();openEditModal('${eName}')">✏️ Bearbeiten</div>
            <div class="row-ctx-item" onclick="event.stopPropagation();toggleFavorite('${eName}',null)">⭐ Favorit</div>
            <div class="row-ctx-item" onclick="event.stopPropagation();toggleArchive('${eName}', ${!proj.archived})">${proj.archived ? '📂 Wiederherstellen' : '📦 Archivieren'}</div>
        </div>
    </div>`;

    tr.innerHTML = `
        <td class="project-name"><span class="pn-icons">${favBtn}${projInfoIcon}</span><span class="pn-text">${namePrefix}${isNew ? '<span class="badge badge-new">NEU</span> ' : ''}${displayName}${typeBadge}${relationBadges}</span></td>
        <td class="project-function">${proj.function || '-'}</td>
        <td>${getGroupBadge(proj.group)}</td>
        <td>${getPriorityBadge(proj.priority)}</td>
        <td>${getDeadlineBadge(proj.deadline)}</td>
        <td>${getProgressBar(proj.progress)}</td>
        <td style="max-width:200px;overflow:hidden">${getMilestones(proj.milestones)}</td>
        <td>${gitBadge}</td>
        <td>${lastActivity}</td>
        <td>${ctxMenu}</td>
    `;
    return tr;
}

function renderProjectsTable(data) {
    const tbody = document.getElementById('tableBody');
    tbody.innerHTML = '';

    const priorityOrder = {'high': 0, 'medium': 1, 'low': 2};

    // Favoriten-Sektion (immer oben, in beiden Ansichten)
    if (favorites.length > 0) {
        const favProjects = data.projects.filter(p => favorites.includes(p.name) && p.project_type !== 'subproject');
        if (favProjects.length > 0) {
            const favHeader = document.createElement('tr');
            favHeader.classList.add('section-header');
            favHeader.innerHTML = '<td colspan="10" style="color:#ffd700">⭐ FAVORITEN</td>';
            tbody.appendChild(favHeader);
            favProjects.forEach(proj => {
                tbody.appendChild(renderProject(proj, data.new_projects.includes(proj.name)));
            });
        }
    }

    // Ansicht basierend auf View-Mode
    if (currentViewMode === 'groups') {
        // === ANSICHT: NACH GRUPPEN ===
        renderByGroups(data, tbody);
    } else {
        // === ANSICHT: NACH PRIORITÄT (Standard) ===
        const projectsWithPriority = data.projects.filter(p => p.priority && p.project_type !== 'subproject');
        const projectsWithoutPriority = data.projects.filter(p => !p.priority && p.project_type !== 'subproject');

        // Sortierung nach Priorität, dann Deadline
        projectsWithPriority.sort((a, b) => {
            const pa = priorityOrder[a.priority] ?? 3;
            const pb = priorityOrder[b.priority] ?? 3;
            if (pa !== pb) return pa - pb;
            return (a.deadline || '9999') > (b.deadline || '9999') ? 1 : -1;
        });

        // TOP Projekte Header
        if (projectsWithPriority.length > 0) {
            const top5Header = document.createElement('tr');
            top5Header.classList.add('section-header', 'top5-header');
            top5Header.innerHTML = '<td colspan="10">🔥 TOP PROJEKTE (mit Priorität)</td>';
            tbody.appendChild(top5Header);

            projectsWithPriority.forEach(proj => {
                tbody.appendChild(renderProject(proj, data.new_projects.includes(proj.name)));
                // Sub-Projekte anzeigen
                renderSubprojects(data, proj.name, tbody);
            });
        }

        // Weitere Projekte Header
        if (projectsWithoutPriority.length > 0) {
            const otherHeader = document.createElement('tr');
            otherHeader.classList.add('section-header');
            otherHeader.innerHTML = '<td colspan="10">📁 WEITERE PROJEKTE</td>';
            tbody.appendChild(otherHeader);

            projectsWithoutPriority.forEach(proj => {
                tbody.appendChild(renderProject(proj, data.new_projects.includes(proj.name)));
                // Sub-Projekte anzeigen
                renderSubprojects(data, proj.name, tbody);
            });
        }
    }
}

function renderByGroups(data, tbody) {
    // Projekte nach Gruppen gruppieren (ohne Sub-Projekte)
    const mainProjects = data.projects.filter(p => p.project_type !== 'subproject');

    // Gruppen-Map erstellen
    const groupedProjects = {};
    groupsData.groups.forEach(g => {
        groupedProjects[g.id] = [];
    });
    groupedProjects['none'] = [];  // Für Projekte ohne Gruppe

    mainProjects.forEach(proj => {
        const groupId = proj.group || 'none';
        if (groupedProjects[groupId]) {
            groupedProjects[groupId].push(proj);
        } else {
            groupedProjects['none'].push(proj);
        }
    });

    // Jede Gruppe rendern
    groupsData.groups.forEach(group => {
        const projects = groupedProjects[group.id] || [];
        if (projects.length === 0) return;

        // Sortierung innerhalb der Gruppe: Priorität > Deadline > Name
        const priorityOrder = {'high': 0, 'medium': 1, 'low': 2};
        projects.sort((a, b) => {
            const pa = priorityOrder[a.priority] ?? 3;
            const pb = priorityOrder[b.priority] ?? 3;
            if (pa !== pb) return pa - pb;
            if (a.deadline && b.deadline) return a.deadline > b.deadline ? 1 : -1;
            if (a.deadline) return -1;
            if (b.deadline) return 1;
            return a.name.localeCompare(b.name);
        });

        // Gruppen-Header mit Farbe
        const header = document.createElement('tr');
        header.classList.add('section-header', 'group-section-header');
        header.style.background = `linear-gradient(135deg, ${group.color}, ${adjustColor(group.color, 30)})`;
        header.innerHTML = `<td colspan="10">${group.icon} ${group.name} <span style="opacity:0.7;font-weight:normal">(${projects.length})</span></td>`;
        tbody.appendChild(header);

        projects.forEach(proj => {
            tbody.appendChild(renderProject(proj, data.new_projects.includes(proj.name)));
            // Sub-Projekte anzeigen
            renderSubprojects(data, proj.name, tbody);
        });
    });

    // Projekte ohne Gruppe
    const noGroupProjects = groupedProjects['none'] || [];
    if (noGroupProjects.length > 0) {
        noGroupProjects.sort((a, b) => a.name.localeCompare(b.name));

        const header = document.createElement('tr');
        header.classList.add('section-header');
        header.innerHTML = `<td colspan="10">📁 Ohne Gruppe <span style="opacity:0.7;font-weight:normal">(${noGroupProjects.length})</span></td>`;
        tbody.appendChild(header);

        noGroupProjects.forEach(proj => {
            tbody.appendChild(renderProject(proj, data.new_projects.includes(proj.name)));
            renderSubprojects(data, proj.name, tbody);
        });
    }
}

function renderSubprojects(data, parentName, tbody) {
    // Sub-Projekte für ein Parent-Projekt rendern
    const subprojects = data.projects.filter(p => p.parent_project === parentName);
    subprojects.forEach(sub => {
        tbody.appendChild(renderProject(sub, data.new_projects.includes(sub.name)));
    });
}

function adjustColor(color, amount) {
    // Farbe aufhellen für Gradient
    const hex = color.replace('#', '');
    const r = Math.min(255, parseInt(hex.substr(0, 2), 16) + amount);
    const g = Math.min(255, parseInt(hex.substr(2, 2), 16) + amount);
    const b = Math.min(255, parseInt(hex.substr(4, 2), 16) + amount);
    return `rgb(${r}, ${g}, ${b})`;
}

function showInfo(type, name) {
    document.getElementById('modalTitle').textContent = name;
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Lade Beschreibung...';
    document.getElementById('infoModal').classList.add('show');

    fetch(`/api/info?type=${type}&name=${encodeURIComponent(name)}`)
        .then(r => r.json())
        .then(data => {
            let html = '<div>' + data.description.replace(/\\n/g, '<br>') + '</div>';
            if (data.source) {
                html += `<div class="modal-source">Quelle: ${data.source}</div>`;
            }
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Fehler beim Laden: ' + err;
        });
}

function closeModal() {
    document.getElementById('infoModal').classList.remove('show');
}

function openTerminal(projectName) {
    fetch(`/api/terminal?project=${encodeURIComponent(projectName)}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('Terminal geöffnet für: ' + projectName);
            } else {
                alert('Fehler: ' + data.error);
            }
        });
}

function refreshDescriptions() {
    document.getElementById('modalTitle').textContent = '📝 Beschreibungen aktualisieren';
    document.getElementById('modalBody').innerHTML = `
        <p>Wähle aus, wie die Projektbeschreibungen aktualisiert werden sollen:</p>
        <div style="margin:20px 0;display:flex;flex-direction:column;gap:10px">
            <button class="btn" onclick="executeRefresh(false)" style="padding:15px">
                <strong>Nur fehlende ergänzen</strong><br>
                <small style="color:#aaa">Beschreibungen werden nur für Projekte ohne Beschreibung generiert</small>
            </button>
            <button class="btn" onclick="executeRefresh(true)" style="padding:15px;background:#8b4513">
                <strong>Alle neu erkennen</strong><br>
                <small style="color:#aaa">Alle Beschreibungen werden aus den Quellen neu extrahiert</small>
            </button>
        </div>
        <button class="btn-cancel" onclick="closeModal()" style="margin-top:10px">Abbrechen</button>
    `;
    document.getElementById('infoModal').classList.add('show');
}

function executeRefresh(forceAll) {
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Scanne Projekte...';

    const url = forceAll ? '/api/projects/refresh?force_descriptions=true' : '/api/projects/refresh';
    fetch(url, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            let html = `<h3>✅ ${data.updated} Projekte aktualisiert</h3>`;
            if (data.force_descriptions) {
                html += '<p style="color:#ffaa00">Alle Beschreibungen wurden neu erkannt.</p>';
            }
            if (data.projects && data.projects.length > 0) {
                html += '<div style="max-height:300px;overflow-y:auto;margin:15px 0">';
                html += '<table style="width:100%;font-size:13px">';
                data.projects.slice(0, 20).forEach(p => {
                    html += `<tr><td style="padding:5px;color:#4dabf7">${p.name}</td><td style="padding:5px;color:#aaa">${p.description || '-'}</td></tr>`;
                });
                if (data.projects.length > 20) {
                    html += `<tr><td colspan="2" style="padding:5px;color:#666">... und ${data.projects.length - 20} weitere</td></tr>`;
                }
                html += '</table></div>';
            }
            if (data.errors && data.errors.length > 0) {
                html += `<p style="color:#ff6666">${data.errors.length} Fehler aufgetreten</p>`;
            }
            html += '<button class="btn" onclick="closeModal();loadData()" style="margin-top:15px">Schließen & Aktualisieren</button>';
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Fehler: ' + err;
        });
}

function cleanupDocker() {
    document.getElementById('modalTitle').textContent = '🧹 Docker Aufräumen';
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Analysiere...';
    document.getElementById('infoModal').classList.add('show');

    // Erst Analyse anzeigen
    fetch('/api/cleanup?mode=analyze')
        .then(r => r.json())
        .then(data => {
            let html = '<h3>📊 Analyse vor Reinigung:</h3><pre>' + data.result + '</pre>';
            html += '<p><a href="/api/cleanup/report?type=pre" target="_blank" class="action-link">📥 Analyse als .md exportieren</a></p>';
            html += '<hr style="border-color:#444;margin:20px 0">';
            html += '<p>Möchtest du die Reinigung durchführen?</p>';
            html += '<button class="btn" onclick="executeCleanup()" style="margin-right:10px">✅ Ja, aufräumen</button>';
            html += '<button class="btn" onclick="closeModal()" style="background:#666">❌ Abbrechen</button>';
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Fehler: ' + err;
        });
}

function executeCleanup() {
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Räume auf...';

    fetch('/api/cleanup?mode=execute')
        .then(r => r.json())
        .then(data => {
            let html = '<h3>✅ Reinigung abgeschlossen:</h3><pre>' + data.result + '</pre>';
            if (data.space_freed) {
                html += '<p><strong>Freigegebener Speicher:</strong> ' + data.space_freed + '</p>';
            }
            html += '<p><a href="/api/cleanup/report?type=post" target="_blank" class="action-link">📥 Bericht als .md exportieren</a></p>';
            document.getElementById('modalBody').innerHTML = html;
            loadData();
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Fehler: ' + err;
        });
}

document.addEventListener('keydown', e => {
    // Escape: Modal schließen oder Suche leeren
    if (e.key === 'Escape') {
        if (document.getElementById('groupsModal').classList.contains('show')) {
            closeGroupsModal();
        } else if (document.getElementById('infoModal').classList.contains('show')) {
            closeModal();
        } else if (document.getElementById('editModal').classList.contains('show')) {
            closeEditModal();
        } else if (currentSearchTerm) {
            clearSearch();
        }
    }
    // Strg+K oder / für Suchfokus (wenn nicht in Input)
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName))) {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }
});

function guessDescription(name, image) {
    const n = name.toLowerCase();
    const i = image.toLowerCase();
    if (n.includes('portainer')) return 'Docker Management UI';
    if (n.includes('traefik')) return 'Reverse Proxy / Load Balancer';
    if (n.includes('nginx')) return 'Web Server / Reverse Proxy';
    if (n.includes('redis')) return 'In-Memory Cache / Message Broker';
    if (n.includes('postgres') || n.includes('mariadb') || n.includes('mysql')) return 'Datenbank';
    if (n.includes('grafana')) return 'Monitoring Dashboard';
    if (n.includes('prometheus')) return 'Metrics Collection';
    if (n.includes('gitea')) return 'Git Server';
    if (n.includes('directus')) return 'Headless CMS';
    if (n.includes('ghost')) return 'Blog Platform';
    if (n.includes('celery') || n.includes('worker')) return 'Background Worker';
    if (n.includes('beat')) return 'Task Scheduler';
    if (i.includes('redis')) return 'Redis Cache';
    if (i.includes('postgres')) return 'PostgreSQL DB';
    if (i.includes('nginx')) return 'Nginx Server';
    return image.split(':')[0].split('/').pop();
}

// Lustige Entwickler-Sprüche
const funnyQuotes = [
    "Mass Container Deployment Unit... 🚀",
    "Suche nach dem fehlenden Semikolon... 🔍",
    "Kaffee wird in Code umgewandelt... ☕",
    "99 little bugs in the code, 99 little bugs... 🐛",
    "Kompiliere Ausreden für den Chef... 📋",
    "Lösche node_modules zum 47. Mal... 📁",
    "Stack Overflow wird konsultiert... 📚",
    "Container werden geweckt... 🐳",
    "Git blame läuft... 🕵️",
    "Versuche Docker zu verstehen... 🤔",
    "README.md wird ignoriert... 📄",
    "Generiere zufällige Bugs... 🎲",
    "Lösche System32... nur Spaß! 😅",
    "Backup? Welches Backup? 💾",
    "Es funktioniert auf meinem Rechner... 🖥️",
    "chmod 777 auf alles... 🔓",
    "sudo make me a sandwich 🥪",
    "while(true) { coffee++; } ☕",
    "DNS propagiert noch... ⏳",
    "Warte auf npm install... 📦"
];

function showFunnyQuote() {
    const quote = funnyQuotes[Math.floor(Math.random() * funnyQuotes.length)];
    document.getElementById('funnyQuote').textContent = quote;
}

// Konfetti-Effekt für neue Projekte
function launchConfetti() {
    const colors = ['#ff0', '#0f0', '#0ff', '#f0f', '#f00', '#00f'];
    for (let i = 0; i < 50; i++) {
        const confetti = document.createElement('div');
        confetti.style.cssText = `
            position: fixed;
            width: 10px;
            height: 10px;
            background: ${colors[Math.floor(Math.random() * colors.length)]};
            left: ${Math.random() * 100}vw;
            top: -10px;
            opacity: 1;
            border-radius: ${Math.random() > 0.5 ? '50%' : '0'};
            pointer-events: none;
            z-index: 9999;
            animation: confettiFall ${2 + Math.random() * 2}s linear forwards;
        `;
        document.body.appendChild(confetti);
        setTimeout(() => confetti.remove(), 4000);
    }
}

// Konfetti Animation
const style = document.createElement('style');
style.textContent = `
    @keyframes confettiFall {
        to {
            top: 100vh;
            opacity: 0;
            transform: rotate(${Math.random() * 720}deg);
        }
    }
`;
document.head.appendChild(style);

// === FILTER & SUCH FUNKTIONEN ===
let currentGroupFilter = 'all';
let currentViewMode = 'priority';  // 'priority' oder 'groups'
let currentSort = { field: 'activity', dir: 'desc' };
let allProjectsData = [];
let currentSearchTerm = '';
let searchDebounceTimer = null;

// View-Mode wechseln
function setViewMode(mode) {
    currentViewMode = mode;
    document.getElementById('viewPriorityBtn').classList.toggle('active', mode === 'priority');
    document.getElementById('viewGroupBtn').classList.toggle('active', mode === 'groups');
    // Daten neu rendern
    if (allProjectsData.projects) {
        renderProjectsTable(allProjectsData);
    }
}

function setGroupFilter(filter, btn) {
    currentGroupFilter = filter;
    document.querySelectorAll('#filterBar .filter-btn').forEach(b => b.classList.remove('active'));
    // btn kann über event.target oder als Parameter kommen
    const targetBtn = btn || event.target;
    if (targetBtn) targetBtn.classList.add('active');
    applyFiltersAndSort();
}

// Live-Suche mit Debounce
function handleSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        const input = document.getElementById('searchInput');
        const clearBtn = document.getElementById('searchClear');
        currentSearchTerm = input.value.trim().toLowerCase();

        // X-Button anzeigen/verstecken
        if (currentSearchTerm) {
            clearBtn.classList.add('show');
        } else {
            clearBtn.classList.remove('show');
        }

        applyFiltersAndSort();
    }, 150); // 150ms Debounce für flüssiges Tippen
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('searchClear').classList.remove('show');
    document.getElementById('searchResults').innerHTML = '';
    currentSearchTerm = '';
    applyFiltersAndSort();
}

function applyFiltersAndSort() {
    const tbody = document.getElementById('tableBody');
    const rows = tbody.querySelectorAll('tr:not(.section-header)');
    let visibleCount = 0;
    let totalCount = rows.length;

    rows.forEach(row => {
        const group = row.dataset.group || '';
        const priority = row.dataset.priority || '';
        const searchText = row.dataset.searchtext || '';
        const isArchived = row.dataset.archived === '1';
        let visible = true;

        // Archiv-Filter: standardmaessig ausblenden
        if (isArchived && !showArchived) {
            visible = false;
        }

        // Gruppenfilter
        if (visible && currentGroupFilter !== 'all') {
            if (currentGroupFilter === 'priority') {
                if (!priority) visible = false;
            } else if (currentGroupFilter === 'none') {
                if (group) visible = false;
            } else if (group !== currentGroupFilter) {
                visible = false;
            }
        }

        // Suchfilter
        if (visible && currentSearchTerm) {
            visible = searchText.includes(currentSearchTerm);
        }

        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
    });

    // Suchergebnis-Anzeige aktualisieren
    const resultsEl = document.getElementById('searchResults');
    if (currentSearchTerm) {
        resultsEl.innerHTML = `<span class="count">${visibleCount}</span> von ${totalCount} Projekten`;
    } else {
        resultsEl.innerHTML = '';
    }

    // Section-Header ausblenden wenn keine sichtbaren Zeilen darunter
    updateSectionHeaders();
}

function updateSectionHeaders() {
    const tbody = document.getElementById('tableBody');
    const headers = tbody.querySelectorAll('tr.section-header');

    headers.forEach(header => {
        let hasVisibleRows = false;
        let nextRow = header.nextElementSibling;

        while (nextRow && !nextRow.classList.contains('section-header')) {
            if (nextRow.style.display !== 'none') {
                hasVisibleRows = true;
                break;
            }
            nextRow = nextRow.nextElementSibling;
        }

        header.style.display = hasVisibleRows ? '' : 'none';
    });
}

// === SORTIER FUNKTIONEN ===
function initSorting() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const field = this.dataset.sort;
            if (currentSort.field === field) {
                currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.dir = 'asc';
            }
            document.querySelectorAll('th.sortable').forEach(h => h.classList.remove('asc', 'desc'));
            this.classList.add(currentSort.dir);
            loadData();
        });
    });
}

// === EDIT MODAL FUNKTIONEN ===
let currentEditProject = null;

function openEditModal(projectName) {
    currentEditProject = projectName;
    document.getElementById('editProjectName').textContent = projectName;
    document.getElementById('editModal').classList.add('show');

    // Gruppen-Dropdown aktualisieren
    updateGroupDropdown();

    // Relation Types laden (falls noch nicht geladen)
    if (relationTypes.length === 0) {
        loadRelationTypes();
    }

    // Tab auf Allgemein setzen
    switchEditTab('general');

    fetch(`/api/project/${encodeURIComponent(projectName)}`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('editDescription').value = data.description || '';
            document.getElementById('editGroup').value = data.group || '';
            document.getElementById('editPriority').value = data.priority || '';
            document.getElementById('editDeadline').value = data.deadline || '';
            document.getElementById('editProgress').value = data.progress !== null ? data.progress : '';

            const milestoneList = document.getElementById('milestoneList');
            milestoneList.innerHTML = '';
            if (data.milestones && data.milestones.length > 0) {
                data.milestones.forEach((m, i) => {
                    addMilestoneRow(m.name, m.done, i);
                });
            }
        })
        .catch(err => {
            console.error('Fehler beim Laden:', err);
        });
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('show');
    currentEditProject = null;
    // Inline-Gruppen-Formular zurücksetzen
    const inlineForm = document.getElementById('inlineGroupForm');
    if (inlineForm) {
        inlineForm.style.display = 'none';
        document.getElementById('inlineGroupId').value = '';
        document.getElementById('inlineGroupName').value = '';
        document.getElementById('inlineGroupIcon').value = '📁';
        document.getElementById('inlineGroupColor').value = '#666666';
    }
    // Relations-Tab zurücksetzen
    switchEditTab('general');
    document.getElementById('editRelationProject').value = '';
    document.getElementById('editRelationNote').value = '';
    document.getElementById('editRelationDropdown').innerHTML = '';
    document.getElementById('editRelationDropdown').style.display = 'none';
}

// === RELATIONS TAB FUNKTIONEN ===
let editRelationSearchTimeout = null;
let editRelationAbortController = null;

function switchEditTab(tab) {
    document.querySelectorAll('.modal-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.edit-tab-content').forEach(content => content.classList.remove('active'));

    if (tab === 'general') {
        document.querySelector('.modal-tab:first-child').classList.add('active');
        document.getElementById('editTabGeneral').classList.add('active');
    } else {
        document.querySelector('.modal-tab:last-child').classList.add('active');
        document.getElementById('editTabRelations').classList.add('active');
        loadProjectRelations();
    }
}

async function loadRelationTypes() {
    const resp = await fetch('/api/relations/types');
    relationTypes = await resp.json();
    const select = document.getElementById('editRelationType');
    select.innerHTML = relationTypes.map(t =>
        `<option value="${t.id}">${t.icon} ${t.name}</option>`
    ).join('');
}

async function loadProjectRelations() {
    if (!currentEditProject) return;

    const resp = await fetch(`/api/project/${encodeURIComponent(currentEditProject)}/relations`);
    const data = await resp.json();

    const outgoingDiv = document.getElementById('outgoingRelations');
    const incomingDiv = document.getElementById('incomingRelations');

    if (data.outgoing.length === 0) {
        outgoingDiv.innerHTML = '<div style="color:#666;font-style:italic">Keine ausgehenden Beziehungen</div>';
    } else {
        outgoingDiv.innerHTML = data.outgoing.map(rel => {
            const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: '🔗', name: rel.type, color: '#888'};
            return `
                <div class="relation-item" style="border-left:3px solid ${typeInfo.color}">
                    <span class="relation-type">${typeInfo.icon} ${typeInfo.name}</span>
                    <span class="relation-target">→ ${rel.target}</span>
                    ${rel.note ? `<span class="relation-note">(${rel.note})</span>` : ''}
                    <button class="btn-remove" onclick="deleteProjectRelation('${rel.id}')" title="Löschen">×</button>
                </div>
            `;
        }).join('');
    }

    if (data.incoming.length === 0) {
        incomingDiv.innerHTML = '<div style="color:#666;font-style:italic">Keine eingehenden Beziehungen</div>';
    } else {
        incomingDiv.innerHTML = data.incoming.map(rel => {
            const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: '🔗', name: rel.type, color: '#888'};
            return `
                <div class="relation-item" style="border-left:3px solid ${typeInfo.color}">
                    <span class="relation-type">${typeInfo.icon} ${typeInfo.name}</span>
                    <span class="relation-target">← ${rel.source}</span>
                    ${rel.note ? `<span class="relation-note">(${rel.note})</span>` : ''}
                    <button class="btn-remove" onclick="deleteProjectRelation('${rel.id}')" title="Löschen">×</button>
                </div>
            `;
        }).join('');
    }
}

function updateRelationForm() {
    const direction = document.querySelector('input[name="relationDirection"]:checked').value;
    document.getElementById('relationTargetLabel').textContent =
        direction === 'outgoing' ? 'Ziel-Projekt' : 'Quell-Projekt';
}

function onEditRelationSearch() {
    clearTimeout(editRelationSearchTimeout);
    if (editRelationAbortController) editRelationAbortController.abort();

    const query = document.getElementById('editRelationProject').value.trim();
    const dropdown = document.getElementById('editRelationDropdown');

    if (query.length < 1) {
        dropdown.style.display = 'none';
        return;
    }

    editRelationSearchTimeout = setTimeout(async () => {
        editRelationAbortController = new AbortController();
        try {
            const resp = await fetch(`/api/projects/search?q=${encodeURIComponent(query)}&limit=10`, {
                signal: editRelationAbortController.signal
            });
            const results = await resp.json();

            // Aktuelles Projekt aus der Liste entfernen
            const filtered = results.filter(p => p.name !== currentEditProject);

            if (filtered.length === 0) {
                dropdown.innerHTML = '<div class="dropdown-item" style="color:#888">Keine Treffer</div>';
            } else {
                dropdown.innerHTML = filtered.map(p => `
                    <div class="dropdown-item" onclick="selectEditRelationProject('${p.name}')">
                        <strong>${p.name}</strong>
                        ${p.description ? `<small style="color:#888;margin-left:8px">${p.description}</small>` : ''}
                    </div>
                `).join('');
            }
            dropdown.style.display = 'block';
        } catch (e) {
            if (e.name !== 'AbortError') console.error(e);
        }
    }, 200);
}

function selectEditRelationProject(name) {
    document.getElementById('editRelationProject').value = name;
    document.getElementById('editRelationDropdown').style.display = 'none';
}

async function addProjectRelation() {
    const targetProject = document.getElementById('editRelationProject').value.trim();
    const relationType = document.getElementById('editRelationType').value;
    const note = document.getElementById('editRelationNote').value.trim();
    const direction = document.querySelector('input[name="relationDirection"]:checked').value;

    if (!targetProject) {
        alert('Bitte ein Projekt auswählen');
        return;
    }

    const source = direction === 'outgoing' ? currentEditProject : targetProject;
    const target = direction === 'outgoing' ? targetProject : currentEditProject;

    const resp = await fetch('/api/relations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, target, type: relationType, note })
    });

    if (resp.ok) {
        document.getElementById('editRelationProject').value = '';
        document.getElementById('editRelationNote').value = '';
        loadProjectRelations();
        loadData(); // Dashboard aktualisieren
    } else {
        const err = await resp.json();
        alert('Fehler: ' + (err.error || 'Unbekannter Fehler'));
    }
}

async function deleteProjectRelation(id) {
    if (!confirm('Beziehung wirklich löschen?')) return;

    const resp = await fetch(`/api/relations/${id}`, { method: 'DELETE' });
    if (resp.ok) {
        loadProjectRelations();
        loadData(); // Dashboard aktualisieren
    }
}

// Dropdown schließen bei Klick außerhalb
document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('editRelationDropdown');
    const input = document.getElementById('editRelationProject');
    if (dropdown && !dropdown.contains(e.target) && e.target !== input) {
        dropdown.style.display = 'none';
    }
});

function addMilestone() {
    const milestoneList = document.getElementById('milestoneList');
    const idx = milestoneList.children.length;
    addMilestoneRow('', false, idx);
}

function addMilestoneRow(name, done, idx) {
    const milestoneList = document.getElementById('milestoneList');
    const div = document.createElement('div');
    div.className = 'milestone-item';
    div.innerHTML = `
        <input type="checkbox" ${done ? 'checked' : ''} data-idx="${idx}">
        <input type="text" value="${name}" placeholder="Meilenstein-Name" data-idx="${idx}">
        <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
    `;
    milestoneList.appendChild(div);
}

function removeMilestone(btn) {
    btn.parentElement.remove();
}

document.getElementById('editForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const milestones = [];
    document.querySelectorAll('#milestoneList .milestone-item').forEach(item => {
        const checkbox = item.querySelector('input[type="checkbox"]');
        const textInput = item.querySelector('input[type="text"]');
        if (textInput.value.trim()) {
            milestones.push({
                name: textInput.value.trim(),
                done: checkbox.checked
            });
        }
    });

    const data = {
        name: currentEditProject,
        description: document.getElementById('editDescription').value,
        group: document.getElementById('editGroup').value || null,
        priority: document.getElementById('editPriority').value || null,
        deadline: document.getElementById('editDeadline').value || null,
        progress: document.getElementById('editProgress').value ? parseInt(document.getElementById('editProgress').value) : null,
        milestones: milestones
    };

    fetch('/api/project/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            closeEditModal();
            loadData();
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => {
        alert('Fehler beim Speichern: ' + err);
    });
});

showFunnyQuote();
// Gruppen + Favoriten laden, dann Projektdaten
Promise.all([loadGroups(), loadFavorites()]).then(() => {
    loadData();
});
initSorting();

// Stille Auto-Refresh Intervalle
setInterval(loadData, 15000);  // Projekt-Daten alle 15 Sekunden
setInterval(loadNews, 30000);  // News alle 30 Sekunden

// ============== IDEEN / NOTIZEN ==============
let ideasData = { ideas: [], categories: [] };
let currentEditIdea = null;

async function loadIdeas() {
    const resp = await fetch('/api/ideas');
    ideasData = await resp.json();
    renderIdeasList();
}

function openIdeasModal() {
    document.getElementById('ideasModal').style.display = 'flex';
    loadIdeas();
}

function closeIdeasModal() {
    document.getElementById('ideasModal').style.display = 'none';
    currentEditIdea = null;
    resetIdeaForm();
}

function resetIdeaForm() {
    document.getElementById('ideaTitle').value = '';
    document.getElementById('ideaContent').value = '';
    document.getElementById('ideaCategory').value = 'note';
    document.getElementById('ideaPriority').value = 'normal';
    document.getElementById('ideaProject').value = '';
    document.getElementById('ideaFormTitle').textContent = 'Neue Idee';
    document.getElementById('ideaSaveBtn').textContent = 'Speichern';
    currentEditIdea = null;
}

function renderIdeasList() {
    const container = document.getElementById('ideasList');
    const filterCategory = document.getElementById('ideasFilterCategory').value;
    const filterStatus = document.getElementById('ideasFilterStatus').value;

    let filtered = ideasData.ideas;
    if (filterCategory) {
        filtered = filtered.filter(i => i.category === filterCategory);
    }
    if (filterStatus) {
        filtered = filtered.filter(i => i.status === filterStatus);
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:#666;padding:40px;">Keine Ideen vorhanden</div>';
        return;
    }

    container.innerHTML = filtered.map(idea => {
        const cat = ideasData.categories.find(c => c.id === idea.category) || {icon: '📝', color: '#666'};
        const priorityIcon = idea.priority === 'high' ? '🔴' : idea.priority === 'low' ? '🟢' : '';
        const statusClass = idea.status === 'done' ? 'idea-done' : idea.status === 'archived' ? 'idea-archived' : '';
        const date = new Date(idea.created).toLocaleDateString('de-DE');
        return `
            <div class="idea-card ${statusClass}" onclick="editIdea('${idea.id}')">
                <div class="idea-header">
                    <span class="idea-cat" style="background:${cat.color}30;color:${cat.color}">${cat.icon}</span>
                    <span class="idea-title">${priorityIcon} ${idea.title}</span>
                    <span class="idea-date">${date}</span>
                </div>
                ${idea.content ? `<div class="idea-content">${idea.content.substring(0, 150)}${idea.content.length > 150 ? '...' : ''}</div>` : ''}
                ${idea.project ? `<div class="idea-project">📁 ${idea.project}</div>` : ''}
                <div class="idea-actions">
                    <button class="idea-status-btn" onclick="event.stopPropagation();toggleIdeaStatus('${idea.id}','${idea.status}')">${idea.status === 'done' ? '↩️ Öffnen' : '✅ Erledigt'}</button>
                    <button class="idea-delete-btn" onclick="event.stopPropagation();deleteIdea('${idea.id}')">🗑️</button>
                </div>
            </div>
        `;
    }).join('');

    // Kategorien für Filter
    document.getElementById('ideasFilterCategory').innerHTML = '<option value="">Alle Kategorien</option>' +
        ideasData.categories.map(c => `<option value="${c.id}">${c.icon} ${c.name}</option>`).join('');

    // Kategorien für Form
    document.getElementById('ideaCategory').innerHTML = ideasData.categories.map(c =>
        `<option value="${c.id}">${c.icon} ${c.name}</option>`
    ).join('');

    // Projekte für Form (aus allProjectsData)
    if (allProjectsData && allProjectsData.projects) {
        const projectOptions = allProjectsData.projects
            .filter(p => p.project_type !== 'subproject')
            .map(p => `<option value="${p.name}">${p.name}</option>`)
            .join('');
        document.getElementById('ideaProject').innerHTML = '<option value="">Kein Projekt</option>' + projectOptions;
    }
}

function editIdea(ideaId) {
    const idea = ideasData.ideas.find(i => i.id === ideaId);
    if (!idea) return;

    currentEditIdea = ideaId;
    document.getElementById('ideaTitle').value = idea.title;
    document.getElementById('ideaContent').value = idea.content || '';
    document.getElementById('ideaCategory').value = idea.category;
    document.getElementById('ideaPriority').value = idea.priority;
    document.getElementById('ideaProject').value = idea.project || '';
    document.getElementById('ideaFormTitle').textContent = 'Idee bearbeiten';
    document.getElementById('ideaSaveBtn').textContent = 'Aktualisieren';
}

async function saveIdea() {
    const title = document.getElementById('ideaTitle').value.trim();
    const content = document.getElementById('ideaContent').value.trim();
    const category = document.getElementById('ideaCategory').value;
    const priority = document.getElementById('ideaPriority').value;
    const project = document.getElementById('ideaProject').value || null;

    if (!title) {
        alert('Bitte einen Titel eingeben');
        return;
    }

    const data = { title, content, category, priority, project };

    if (currentEditIdea) {
        // Update
        await fetch(`/api/ideas/${currentEditIdea}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    } else {
        // Create
        await fetch('/api/ideas', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    }

    resetIdeaForm();
    loadIdeas();
}

async function deleteIdea(ideaId) {
    if (!confirm('Idee wirklich löschen?')) return;
    await fetch(`/api/ideas/${ideaId}`, { method: 'DELETE' });
    loadIdeas();
}

async function toggleIdeaStatus(ideaId, currentStatus) {
    const newStatus = currentStatus === 'done' ? 'open' : 'done';
    await fetch(`/api/ideas/${ideaId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ status: newStatus })
    });
    loadIdeas();
}

function filterIdeas() {
    renderIdeasList();
}
