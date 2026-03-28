// Index-Seite UI: Stats, More-Menu
// Lightbox, Sidebar, Command Palette sind in base.js (global)

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
    openModal('statsModal');
}
function closeStatsModal() {
    closeModal('statsModal');
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
