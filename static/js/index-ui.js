// Index-Seite UI: Lightbox, Stats, More-Menu, Sidebar, Command Palette

// Lightbox
function openLightbox(src) {
    document.getElementById('lightboxImg').src = src;
    document.getElementById('lightbox').classList.add('show');
}
function closeLightbox() {
    document.getElementById('lightbox').classList.remove('show');
}
document.addEventListener('click', function(e) {
    if (e.target.tagName === 'IMG' && !e.target.closest('.lightbox') && !e.target.closest('.sidebar')) {
        e.preventDefault();
        e.stopPropagation();
        openLightbox(e.target.src);
    }
}, true);
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && document.getElementById('lightbox').classList.contains('show')) {
        closeLightbox();
        e.stopPropagation();
    }
}, true);

// Stats Modal
function openStatsModal() {
    var grid = document.getElementById('statsGrid');
    grid.innerHTML = [
        {label:'Projekte', id:'totalProjects', color:'#4fc3f7'},
        {label:'Container', id:'totalContainers', color:'#fff'},
        {label:'Aktiv', id:'runningContainers', color:'#4caf50'},
        {label:'Unhealthy', id:'unhealthyContainers', color:'#ff9800'},
        {label:'Gestoppt', id:'stoppedContainers', color:'#f44336'},
        {label:'Gitea Repos', id:'giteaRepos', color:'#85e085'},
    ].map(function(s) {
        var val = document.getElementById(s.id).textContent;
        return '<div class="stat"><span class="stat-label">' + s.label + '</span><span class="stat-value" style="color:' + s.color + '">' + val + '</span></div>';
    }).join('');
    document.getElementById('statsModal').classList.add('show');
}
function closeStatsModal() {
    document.getElementById('statsModal').classList.remove('show');
}

// More-Menu
function toggleMoreMenu() {
    document.getElementById('moreMenu').classList.toggle('show');
}
document.addEventListener('click', function(e) {
    if (!e.target.closest('.topbar-more')) {
        var m = document.getElementById('moreMenu');
        if (m) m.classList.remove('show');
    }
});

// Sidebar Toggle
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
    document.querySelector('.main-content').classList.toggle('sidebar-collapsed');
    localStorage.setItem('sidebar-collapsed', document.getElementById('sidebar').classList.contains('collapsed'));
}
if (localStorage.getItem('sidebar-collapsed') === 'true') {
    document.getElementById('sidebar').classList.add('collapsed');
    document.querySelector('.main-content').classList.add('sidebar-collapsed');
}

// Command Palette
function openCommandPalette() {
    document.getElementById('cmdOverlay').classList.add('show');
    document.getElementById('cmdInput').value = '';
    document.getElementById('cmdInput').focus();
    resetCmdResults();
}
function closeCommandPalette() {
    document.getElementById('cmdOverlay').classList.remove('show');
}
function resetCmdResults() {
    document.getElementById('cmdResults').innerHTML =
        '<div class="cmd-group"><div class="cmd-group-label">Schnellzugriff</div>' +
        '<div class="cmd-item" onclick="location.href=\'/sessions\'">Claude Sessions</div>' +
        '<div class="cmd-item" onclick="location.href=\'/containers\'">Container</div>' +
        '<div class="cmd-item" onclick="location.href=\'/dependencies\'">Abhaengigkeiten</div>' +
        '<div class="cmd-item" onclick="openIdeasModal();closeCommandPalette()">Ideen & Notizen</div>' +
        '<div class="cmd-item" onclick="loadData();closeCommandPalette()">Daten aktualisieren</div></div>';
}
function handleCmdSearch() {
    const q = document.getElementById('cmdInput').value.trim().toLowerCase();
    if (!q) { resetCmdResults(); return; }
    fetch('/api/projects/search?q=' + encodeURIComponent(q) + '&limit=8')
        .then(r => r.json())
        .then(results => {
            let html = '';
            if (results.length > 0) {
                html += '<div class="cmd-group"><div class="cmd-group-label">Projekte</div>';
                results.forEach(p => {
                    html += '<div class="cmd-item" onclick="openEditModal(\'' + p.name + '\');closeCommandPalette()">' + p.name + ' <span style="color:#666;font-size:11px;margin-left:8px">' + (p.description || '') + '</span></div>';
                });
                html += '</div>';
            }
            const statics = [
                {label:'Claude Sessions', url:'/sessions'},
                {label:'Container', url:'/containers'},
                {label:'Abhaengigkeiten', url:'/dependencies'},
                {label:'Vorlagen', url:'/vorlagen'},
            ].filter(s => s.label.toLowerCase().includes(q));
            if (statics.length > 0) {
                html += '<div class="cmd-group"><div class="cmd-group-label">Seiten</div>';
                statics.forEach(s => { html += '<div class="cmd-item" onclick="location.href=\'' + s.url + '\'">' + s.label + '</div>'; });
                html += '</div>';
            }
            if (!html) html = '<div style="padding:20px;text-align:center;color:#555">Keine Ergebnisse</div>';
            document.getElementById('cmdResults').innerHTML = html;
        });
}

// Ctrl+K Handler
document.addEventListener('keydown', function(e) {
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName))) {
        e.preventDefault();
        if (document.getElementById('cmdOverlay').classList.contains('show')) {
            closeCommandPalette();
        } else {
            openCommandPalette();
        }
    }
    if (e.key === 'Escape' && document.getElementById('cmdOverlay').classList.contains('show')) {
        closeCommandPalette();
        e.stopPropagation();
    }
}, true);
