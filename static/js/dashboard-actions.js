// === DASHBOARD ACTIONS ===
// Favoriten, Archiv, Context-Menu, Info-Modal, Terminal, Refresh, Cleanup

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
            btn.innerHTML = '<i data-lucide="star" class="icon"></i>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
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
        btn.innerHTML = showArchived ? '<i data-lucide="package" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Archiv ausblenden' : '<i data-lucide="package" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Archiv anzeigen';
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
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Lade Beschreibung...';
    openModal('infoModal');

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

function closeInfoModal() {
    closeModal('infoModal');
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
    document.getElementById('modalTitle').textContent = 'Beschreibungen aktualisieren';
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
        <button class="btn-cancel" onclick="closeInfoModal()" style="margin-top:10px">Abbrechen</button>
    `;
    openModal('infoModal');
}

function executeRefresh(forceAll) {
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Scanne Projekte...';

    const url = forceAll ? '/api/projects/refresh?force_descriptions=true' : '/api/projects/refresh';
    fetch(url, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            let html = `<h3>${data.updated} Projekte aktualisiert</h3>`;
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
            html += '<button class="btn" onclick="closeInfoModal();loadData()" style="margin-top:15px">Schließen & Aktualisieren</button>';
            document.getElementById('modalBody').innerHTML = html;
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Fehler: ' + err;
        });
}

function cleanupDocker() {
    document.getElementById('modalTitle').textContent = 'Docker Aufräumen';
    document.getElementById('modalBody').innerHTML = '<div class="spinner"></div> Analysiere...';
    openModal('infoModal');

    // Erst Analyse anzeigen
    fetch('/api/cleanup?mode=analyze')
        .then(r => r.json())
        .then(data => {
            let html = '<h3>Analyse vor Reinigung:</h3><pre>' + data.result + '</pre>';
            html += '<p><a href="/api/cleanup/report?type=pre" target="_blank" class="action-link"><i data-lucide="download" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Analyse als .md exportieren</a></p>';
            html += '<hr style="border-color:#444;margin:20px 0">';
            html += '<p>Möchtest du die Reinigung durchführen?</p>';
            html += '<button class="btn" onclick="executeCleanup()" style="margin-right:10px"><i data-lucide="check" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Ja, aufräumen</button>';
            html += '<button class="btn" onclick="closeInfoModal()" style="background:#666"><i data-lucide="x" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Abbrechen</button>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
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
            let html = '<h3>Reinigung abgeschlossen:</h3><pre>' + data.result + '</pre>';
            if (data.space_freed) {
                html += '<p><strong>Freigegebener Speicher:</strong> ' + data.space_freed + '</p>';
            }
            html += '<p><a href="/api/cleanup/report?type=post" target="_blank" class="action-link"><i data-lucide="download" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> Bericht als .md exportieren</a></p>';
            if (typeof lucide !== 'undefined') lucide.createIcons();
            document.getElementById('modalBody').innerHTML = html;
            loadData();
        })
        .catch(err => {
            document.getElementById('modalBody').innerHTML = 'Fehler: ' + err;
        });
}
