// === DASHBOARD TABLE ===
// Helper functions and table rendering

// === GLOBALE HELPER-FUNKTIONEN FÜR TABELLEN-RENDERING ===

function getPriorityBadge(priority) {
    if (priority === 'high') return '<span class="priority-high"><i data-lucide="arrow-up" class="icon-priority icon-priority-high"></i></span>';
    if (priority === 'medium') return '<span class="priority-medium"><i data-lucide="minus" class="icon-priority icon-priority-medium"></i></span>';
    if (priority === 'low') return '<span class="priority-low"><i data-lucide="arrow-down" class="icon-priority icon-priority-low"></i></span>';
    return '-';
}

function getDeadlineBadge(deadline) {
    if (!deadline) return '-';
    const today = new Date();
    const dl = new Date(deadline);
    const days = Math.ceil((dl - today) / (1000 * 60 * 60 * 24));
    const parts = deadline.split('-');
    const formatted = parts[2] + '.' + parts[1] + '.' + parts[0].substring(2);
    if (days < 0) return `<span class="deadline-urgent" style="white-space:nowrap"><i data-lucide="alert-triangle" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> ${formatted}</span>`;
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
        const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: 'link', color: '#888'};
        badges += `<span class="relation-badge" style="background:${typeInfo.color}" title="${typeInfo.name || rel.type} → ${rel.target}${rel.note ? ': ' + rel.note : ''}">${renderIcon(typeInfo.icon)}</span>`;
    });

    incoming.forEach(rel => {
        const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: 'link', color: '#888'};
        badges += `<span class="relation-badge incoming" style="background:${typeInfo.color}" title="${typeInfo.name || rel.type} ← ${rel.source}${rel.note ? ': ' + rel.note : ''}">${renderIcon(typeInfo.icon)}</span>`;
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

    // Klickbare Zeile -> Projekt-Detail
    tr.style.cursor = 'pointer';
    tr.addEventListener('click', (e) => {
        if (e.target.closest('button, .row-ctx-menu, a, .fav-btn, .info-icon')) return;
        location.href = '/project/' + encodeURIComponent(proj.name);
    });

    // Sub-Projekt Styling
    const isSubproject = proj.project_type === 'subproject';
    if (isSubproject) {
        tr.classList.add('subproject-row');
    }

    // Git Badge (kompakt)
    let gitBadge = '';
    if (proj.sync_status === 'synced') gitBadge = '<span class="badge" style="background:#0066cc;font-size:10px">✓</span>';
    else if (proj.sync_status === 'differs') gitBadge = '<span class="badge" style="background:#cc3300;font-size:10px">⚠</span>';
    else if (proj.git_status === 'geändert' || proj.git_status === 'modified') gitBadge = '<span class="badge" style="background:#8b4513;font-size:10px">M</span>';
    else if (proj.git_status === 'sauber' || proj.git_status === 'clean') gitBadge = '<span class="badge" style="background:#2d5a2d;font-size:10px">✓</span>';

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

    // Version-Badge
    let versionBadge = '';
    if (proj.version) {
        versionBadge = `<span class="badge" style="background:#1a3a2a;color:#4caf50;font-size:9px;margin-left:5px">v${proj.version}</span>`;
    }

    // Activity-Dot (Sprint 2)
    let activityDot = '';
    if (proj.activity_score) {
        const levelColors = {hot:'#ff4444', active:'#4caf50', moderate:'#ff9800', low:'#666', inactive:'#333'};
        const levelTitles = {hot:'Very active', active:'Active', moderate:'Moderate', low:'Low activity', inactive:'Inactive'};
        const lvl = proj.activity_score.level || 'inactive';
        const c7 = proj.activity_score.commits_7d || 0;
        const c30 = proj.activity_score.commits_30d || 0;
        activityDot = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${levelColors[lvl]};margin-right:4px;vertical-align:middle" title="${levelTitles[lvl]} (${c7} commits/7d, ${c30}/30d)"></span>`;
    }

    // Branch-Count Badge (Sprint 2)
    let branchBadge = '';
    if (proj.branch_count && proj.branch_count > 1) {
        branchBadge = `<span class="badge" style="background:#1a2a4a;color:#64b5f6;font-size:9px;margin-left:5px" title="${proj.branch_count} branches">${proj.branch_count}B</span>`;
    }

    // Port-Konflikt Warnung (Sprint 2)
    let portWarnBadge = '';
    if (proj.port_conflict && proj.port_conflict.length > 0) {
        portWarnBadge = `<span class="badge" style="background:#4a1a1a;color:#ff5252;font-size:9px;margin-left:5px" title="Port conflict with: ${proj.port_conflict.join(', ')}">PORT!</span>`;
    }

    // GitHub-Badge (Sprint 3)
    let githubBadge = '';
    if (proj.github) {
        const gh = proj.github;
        const parts = [];
        if (gh.stars > 0) parts.push(`★${gh.stars}`);
        if (gh.open_issues > 0) parts.push(`I:${gh.open_issues}`);
        if (gh.open_prs > 0) parts.push(`PR:${gh.open_prs}`);
        if (parts.length > 0) {
            githubBadge = `<span class="badge" style="background:#222;color:#e0e0e0;font-size:9px;margin-left:5px" title="GitHub: ${gh.full_name}">${parts.join(' ')}</span>`;
        } else {
            githubBadge = `<span class="badge" style="background:#222;color:#888;font-size:9px;margin-left:5px" title="GitHub: ${gh.full_name}">GH</span>`;
        }
    }

    // CI/CD-Badge (Sprint 3)
    let ciBadge = '';
    if (proj.github && proj.github.ci_status) {
        const ciColors = {success:'#1b5e20', failure:'#b71c1c', cancelled:'#4a4a00', in_progress:'#0d47a1'};
        const ciIcons = {success:'✓', failure:'✗', cancelled:'—', in_progress:'⟳'};
        const conclusion = proj.github.ci_conclusion || proj.github.ci_status;
        const color = ciColors[conclusion] || '#333';
        const icon = ciIcons[conclusion] || '?';
        ciBadge = `<span class="badge" style="background:${color};font-size:9px;margin-left:3px" title="CI: ${proj.github.ci_workflow || 'Actions'} — ${conclusion}">${icon}CI</span>`;
    }

    // Health-Badge (Sprint 3)
    let healthBadge = '';
    if (proj.health) {
        const hColors = {up:'#1b5e20', down:'#b71c1c', error:'#e65100'};
        const hIcons = {up:'▲', down:'▼', error:'!'};
        const s = proj.health.status;
        healthBadge = `<span class="badge" style="background:${hColors[s] || '#333'};font-size:9px;margin-left:3px" title="Health: ${proj.health.url} (${proj.health.ms}ms)">${hIcons[s] || '?'}${proj.health.code || ''}</span>`;
    }

    // LOC + Lizenz + Size als Tooltip-Info in Beschreibung
    let metaInfo = '';
    const metaParts = [];
    if (proj.loc_stats && proj.loc_stats.total) {
        const loc = proj.loc_stats.total;
        metaParts.push(loc >= 1000 ? (loc/1000).toFixed(1) + 'k LOC' : loc + ' LOC');
    }
    if (proj.license) metaParts.push(proj.license);
    if (proj.repo_size) metaParts.push(proj.repo_size);
    if (metaParts.length > 0) {
        metaInfo = `<span style="color:#555;font-size:10px;margin-left:6px">${metaParts.join(' · ')}</span>`;
    }

    const isFav = favorites.includes(proj.name);
    const favBtn = `<button class="fav-btn ${isFav ? 'active' : ''}" onclick="event.stopPropagation();toggleFavorite('${proj.name}',this)" title="Favorit"><i data-lucide="star" class="icon"></i></button>`;
    const projInfoIcon = `<span class="info-icon" onclick="event.stopPropagation();location.href='/project/${encodeURIComponent(proj.name)}'" title="Details"><i data-lucide="info" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i></span>`;

    const relationBadges = getRelationBadges(proj.name);

    // Escaped name for JS strings
    const eName = proj.name.replace(/'/g, "\\'");

    const ctxMenu = `<div class="row-ctx">
        <button class="row-ctx-btn" onclick="openRowCtx(event,'${eName}')" title="Aktionen"><i data-lucide="more-horizontal" class="icon"></i></button>
        <div class="row-ctx-menu">
            <div class="row-ctx-item" onclick="event.stopPropagation();location.href='/project/${encodeURIComponent(eName)}'"><i data-lucide="info" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Details</div>
            <div class="row-ctx-item" onclick="event.stopPropagation();openEditModal('${eName}')"><i data-lucide="edit" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Edit</div>
            <div class="row-ctx-item" onclick="event.stopPropagation();toggleFavorite('${eName}',null)"><i data-lucide="star" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Favorite</div>
            <div class="row-ctx-item" onclick="event.stopPropagation();toggleArchive('${eName}', ${!proj.archived})">${proj.archived ? '<i data-lucide="folder-open" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Restore' : '<i data-lucide="package" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Archive'}</div>
        </div>
    </div>`;

    tr.innerHTML = `
        <td class="project-name"><span class="pn-icons">${favBtn}</span><span class="pn-text">${activityDot}${namePrefix}${isNew ? '<span class="badge badge-new">NEU</span> ' : ''}${displayName}${typeBadge}${versionBadge}${branchBadge}${portWarnBadge}${githubBadge}${ciBadge}${healthBadge}${relationBadges}</span></td>
        <td class="project-function">${proj.function || '-'}${metaInfo}</td>
        <td>${getGroupBadge(proj.group)}</td>
        <td>${getPriorityBadge(proj.priority)}</td>
        <td>${getDeadlineBadge(proj.deadline)}</td>
        <td>${getProgressBar(proj.progress)}</td>
        <td style="max-width:200px;overflow:hidden">${getMilestones(proj.milestones)}</td>
        <td>${gitBadge}</td>
        <td>${lastActivity}</td>
        <td>${projInfoIcon}${ctxMenu}</td>
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
            favHeader.innerHTML = '<td colspan="10" style="color:#ffd700"><i data-lucide="star" class="icon" style="width:16px;height:16px;display:inline-block;vertical-align:middle"></i> FAVORITEN</td>';
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
        // === ANSICHT: NACH PRIORITAET (Standard) ===
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
            top5Header.innerHTML = '<td colspan="10"><i data-lucide="flame" class="icon" style="width:16px;height:16px;display:inline-block;vertical-align:middle"></i> TOP PROJECTS (with priority)</td>';
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
            otherHeader.innerHTML = '<td colspan="10"><i data-lucide="folder" class="icon" style="width:16px;height:16px;display:inline-block;vertical-align:middle"></i> MORE PROJECTS</td>';
            tbody.appendChild(otherHeader);

            projectsWithoutPriority.forEach(proj => {
                tbody.appendChild(renderProject(proj, data.new_projects.includes(proj.name)));
                // Sub-Projekte anzeigen
                renderSubprojects(data, proj.name, tbody);
            });
        }
    }

    // Lucide Icons rendern nach DOM-Update
    if (typeof lucide !== 'undefined') lucide.createIcons();
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
        header.innerHTML = `<td colspan="10"><i data-lucide="folder" class="icon" style="width:16px;height:16px;display:inline-block;vertical-align:middle"></i> No Group <span style="opacity:0.7;font-weight:normal">(${noGroupProjects.length})</span></td>`;
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
