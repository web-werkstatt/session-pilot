// Index-Seite UI: Lightbox, Stats, More-Menu
// Sidebar + Command Palette sind in base.js (global)

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
