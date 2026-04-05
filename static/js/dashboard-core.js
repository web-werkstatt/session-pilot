// === DASHBOARD CORE ===
// loadData, renderData, showTab, init block

var _dashboardViewMeta = {
    projects: {
        title: 'Project List',
        subtitle: 'Primaere Arbeitsliste fuer Projekte und Projekteinstieg.'
    },
    widgets: {
        title: 'Project Overview',
        subtitle: 'Verdichtete Projekt-Signale, Aktivitaet und operative Uebersicht.'
    },
    gitea: {
        title: 'Repository Sources',
        subtitle: 'Externe Repository-Quellen als Projekt- und Integrationssicht.'
    }
};

function loadData() {
    // Nur beim ersten Laden den Spinner zeigen
    if (firstLoad) {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('projectTable').style.display = 'none';
    }

    // Daten und Relations parallel laden
    Promise.all([
        api.get('/api/data'),
        api.get('/api/relations')
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
            console.error('Loading failed:', err);
            if (firstLoad) {
                setTimeout(loadData, 2000);
            }
        });
}

// Tab-Funktion
function showTab(tabName, triggerEl) {
    if (!document.getElementById(tabName + 'Tab')) tabName = 'projects';
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(tabName + 'Tab').classList.add('active');
    var titleEl = document.getElementById('dashboardViewTitle');
    var subtitleEl = document.getElementById('dashboardViewSubtitle');
    var filterBar = document.getElementById('filterBar');
    var meta = _dashboardViewMeta[tabName] || _dashboardViewMeta.projects;
    if (titleEl) titleEl.textContent = meta.title;
    if (subtitleEl) subtitleEl.textContent = meta.subtitle;
    if (filterBar) filterBar.style.display = tabName === 'projects' ? '' : 'none';
    if (window.history && window.history.replaceState) {
        var url = tabName === 'projects' ? '/' : ('/?tab=' + encodeURIComponent(tabName));
        window.history.replaceState(null, '', url);
    }
    document.querySelectorAll('#projectsSubmenu .nav-item').forEach(function(item) { item.classList.remove('active'); });
    if (triggerEl && triggerEl.classList) triggerEl.classList.add('active');
    else {
        var activeLink = document.querySelector('#projectsSubmenu .nav-item[href="/?tab=' + tabName + '"]');
        if (tabName === 'projects') activeLink = document.querySelector('#projectsSubmenu .nav-item[href="/?tab=projects"]');
        if (activeLink) activeLink.classList.add('active');
    }
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
    document.getElementById('timestamp').textContent = 'As of: ' + data.timestamp;

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
                <td><a href="${repo.html_url}" target="_blank" class="action-link">Open</a></td>
            `;
            giteaBody.appendChild(tr);
        });
    } else {
        giteaBody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#888">No Gitea repos found</td></tr>';
    }

    // New projects bar mit Konfetti!
    const newBar = document.getElementById('newProjectsBar');
    if (data.new_projects.length > 0) {
        newBar.textContent = '🆕 ' + data.new_projects.length + ' new project' + (data.new_projects.length > 1 ? 's' : '') + ': ' + data.new_projects.slice(0,5).join(', ') + (data.new_projects.length > 5 ? '...' : '');
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

// === INIT BLOCK ===
showFunnyQuote();
showTab(window.INITIAL_DASHBOARD_TAB || 'projects');
// Gruppen + Favoriten laden, dann Projektdaten
Promise.all([loadGroups(), loadFavorites()]).then(() => {
    loadData();
});
initSorting();

// Stille Auto-Refresh Intervalle
setInterval(loadData, 15000);  // Projekt-Daten alle 15 Sekunden
setInterval(loadNews, 30000);  // News alle 30 Sekunden
