// === DASHBOARD CORE ===
// loadData, renderData, showTab, init block

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

// === INIT BLOCK ===
showFunnyQuote();
// Gruppen + Favoriten laden, dann Projektdaten
Promise.all([loadGroups(), loadFavorites()]).then(() => {
    loadData();
});
initSorting();

// Stille Auto-Refresh Intervalle
setInterval(loadData, 15000);  // Projekt-Daten alle 15 Sekunden
setInterval(loadNews, 30000);  // News alle 30 Sekunden
