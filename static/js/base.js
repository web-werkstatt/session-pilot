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

// Lightbox mit Navigation
var lbImages = [];
var lbIndex = 0;

function getLightbox() {
    return document.getElementById('lightbox');
}


function collectLightboxImages(clickedSrc) {
    var imgs = document.querySelectorAll('img:not(.lightbox img):not(.sidebar img):not([src*="favicon"])');
    lbImages = [];
    var foundIdx = 0;
    imgs.forEach(function(img) {
        var src = img.src || img.dataset.src;
        if (!src || img.offsetParent === null) return;
        if (img.naturalWidth < 20 && img.naturalWidth > 0) return;
        lbImages.push({src: src, alt: img.alt || ''});
        if (src === clickedSrc) foundIdx = lbImages.length - 1;
    });
    if (lbImages.length === 0 || !lbImages.some(function(i) { return i.src === clickedSrc; })) {
        var galleryItems = document.querySelectorAll('.doc-gallery-item');
        if (galleryItems.length > 0) {
            lbImages = [];
            galleryItems.forEach(function(item) {
                var img = item.querySelector('img');
                var label = item.querySelector('.gallery-label');
                if (img) lbImages.push({src: img.src, alt: label ? label.textContent : ''});
            });
            lbImages.forEach(function(i, idx) { if (i.src === clickedSrc) foundIdx = idx; });
        }
    }
    return foundIdx;
}

function openLightbox(src) {
    var lightbox = getLightbox();
    if (!lightbox) return;
    lbIndex = collectLightboxImages(src);
    showLightboxImage();
    lightbox.classList.add('show');
}

function showLightboxImage() {
    if (lbImages.length === 0) return;
    var lightboxImg = document.getElementById('lightboxImg');
    var info = document.getElementById('lbInfo');
    var counter = document.getElementById('lbCounter');
    if (!lightboxImg || !info || !counter) return;
    var item = lbImages[lbIndex];
    lightboxImg.src = item.src;
    info.textContent = item.alt || '';
    if (lbImages.length > 1) {
        counter.textContent = (lbIndex + 1) + ' / ' + lbImages.length;
        document.getElementById('lbPrev').style.display = lbIndex > 0 ? '' : 'none';
        document.getElementById('lbNext').style.display = lbIndex < lbImages.length - 1 ? '' : 'none';
        counter.style.display = '';
    } else {
        document.getElementById('lbPrev').style.display = 'none';
        document.getElementById('lbNext').style.display = 'none';
        counter.style.display = 'none';
    }
}

function lightboxNav(dir) {
    lbIndex = Math.max(0, Math.min(lbImages.length - 1, lbIndex + dir));
    showLightboxImage();
}

function closeLightbox() {
    var lightbox = getLightbox();
    var lightboxImg = document.getElementById('lightboxImg');
    if (!lightbox || !lightboxImg) return;
    lightbox.classList.remove('show');
    lightboxImg.src = '';
}

document.addEventListener('click', function(e) {
    if (!getLightbox()) return;
    if (e.target.tagName === 'IMG' && !e.target.closest('.lightbox') && !e.target.closest('.sidebar')) {
        e.preventDefault(); e.stopPropagation(); openLightbox(e.target.src);
    }
}, true);

document.addEventListener('keydown', function(e) {
    var lightbox = getLightbox();
    if (!lightbox || !lightbox.classList.contains('show')) return;
    if (e.key === 'ArrowLeft') { lightboxNav(-1); e.preventDefault(); }
    else if (e.key === 'ArrowRight') { lightboxNav(1); e.preventDefault(); }
});

// Command Palette
function openCommandPalette() {
    document.getElementById('cmdOverlay').classList.add('show');
    document.getElementById('cmdInput').value = '';
    document.getElementById('cmdInput').focus();
    resetCmdResults();
}
function closeCommandPalette() { document.getElementById('cmdOverlay').classList.remove('show'); }
function resetCmdResults() {
    document.getElementById('cmdResults').innerHTML =
        '<div class="cmd-group"><div class="cmd-group-label">Quick Access</div>' +
        '<div class="cmd-item" onclick="location.href=\'/\'">&#128202; Dashboard</div>' +
        '<div class="cmd-item" onclick="location.href=\'/sessions\'">&#129302; Claude Sessions</div>' +
        '<div class="cmd-item" onclick="location.href=\'/sessions/analysis\'">&#128200; Session Analysis</div>' +
        '<div class="cmd-item" onclick="location.href=\'/containers\'">&#128051; Containers</div>' +
        '<div class="cmd-item" onclick="location.href=\'/dependencies\'">&#128279; Dependencies</div>' +
        '<div class="cmd-item" onclick="location.href=\'/vorlagen\'">&#128230; Templates</div>' +
        '<div class="cmd-item" onclick="location.href=\'/news\'">&#128240; News</div></div>';
}
var cmdActiveTab = 'projects';
var cmdSearchTimer = null;

function switchCmdTab(tab) {
    cmdActiveTab = tab;
    document.querySelectorAll('.cmd-tab').forEach(function(t) { t.classList.toggle('active', t.dataset.tab === tab); });
    handleCmdSearch();
}

function handleCmdSearch() {
    var q = document.getElementById('cmdInput').value.trim().toLowerCase();
    if (!q) {
        resetCmdResults();
        document.getElementById('cmdTabs').style.display = 'none';
        return;
    }

    clearTimeout(cmdSearchTimer);
    cmdSearchTimer = setTimeout(function() { doProjectSearch(q); }, 400);
}

function doProjectSearch(q) {
    // Projekte + Seiten + Sessions parallel suchen
    var projectsReq = api.get('/api/projects/search?q=' + encodeURIComponent(q) + '&limit=8');
    var sessionsReq = q.length >= 2
        ? api.get('/api/sessions/search?q=' + encodeURIComponent(q) + '&limit=10').catch(function() { return {results:[]}; })
        : Promise.resolve({results:[]});

    Promise.all([projectsReq, sessionsReq]).then(function(res) {
        var results = res[0];
        var sessData = res[1];
        var html = '';

        if (results.length > 0) {
            html += '<div class="cmd-group"><div class="cmd-group-label">Projects</div>';
            results.forEach(function(p) {
                html += '<div class="cmd-item" onclick="location.href=\'/project/' + encodeURIComponent(p.name) + '\'">&#128193; ' + p.name + ' <span style="color:#666;font-size:11px;margin-left:8px">' + (p.description || '') + '</span></div>';
            });
            html += '</div>';
        }

        var statics = [
            {label:'Dashboard', icon:'&#128202;', url:'/'},
            {label:'Claude Sessions', icon:'&#129302;', url:'/sessions'},
            {label:'Session Analysis', icon:'&#128200;', url:'/sessions/analysis'},
            {label:'Containers', icon:'&#128051;', url:'/containers'},
            {label:'Dependencies', icon:'&#128279;', url:'/dependencies'},
            {label:'Templates', icon:'&#128230;', url:'/vorlagen'},
            {label:'News', icon:'&#128240;', url:'/news'},
        ].filter(function(s) { return s.label.toLowerCase().includes(q); });
        if (statics.length > 0) {
            html += '<div class="cmd-group"><div class="cmd-group-label">Pages</div>';
            statics.forEach(function(s) { html += '<div class="cmd-item" onclick="location.href=\'' + s.url + '\'">' + s.icon + ' ' + s.label + '</div>'; });
            html += '</div>';
        }

        if (sessData.results && sessData.results.length > 0) {
            var re = new RegExp('(' + q.split(/\s+/).map(function(w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')', 'gi');
            html += '<div class="cmd-group"><div class="cmd-group-label">Sessions (' + sessData.total + ' results)</div>';
            sessData.results.forEach(function(s) {
                var date = s.started_at ? new Date(s.started_at).toLocaleDateString('en-US', {month:'short',day:'numeric',year:'2-digit'}) : '';
                var snippet = (s.snippet || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                snippet = snippet.replace(re, '<mark style="background:rgba(79,195,247,0.3);color:#fff;padding:0 2px;border-radius:2px">$1</mark>');
                html += '<div class="cmd-item" onclick="location.href=\'/sessions/' + s.session_uuid + '\'" style="flex-direction:column;align-items:flex-start;gap:4px">';
                html += '<div style="display:flex;gap:8px;align-items:center;width:100%">';
                html += '<span>&#129302;</span>';
                html += '<span style="color:#4fc3f7;font-weight:500">' + (s.project_name || '-') + '</span>';
                html += '<span style="color:#666;font-size:11px">' + date + '</span>';
                html += '<span style="color:#555;font-size:11px">' + (s.duration_formatted || '') + '</span>';
                html += '</div>';
                html += '<div style="font-size:11px;color:#888;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;padding-left:28px">...' + snippet.substring(0, 200) + '...</div>';
                html += '</div>';
            });
            html += '</div>';
        }

        if (!html) html = '<div style="padding:20px;text-align:center;color:#555">No results</div>';
        document.getElementById('cmdResults').innerHTML = html;
    });
}

function doFulltextSearch(q) {
    if (q.length < 2) {
        document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#555">Enter at least 2 characters</div>';
        return;
    }
    document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#555"><span class="doc-status-spinner" style="display:inline-block;width:16px;height:16px;border-width:2px;vertical-align:middle;margin-right:8px"></span>Searching all projects...</div>';

    api.get('/api/search?q=' + encodeURIComponent(q) + '&limit=30')
        .then(function(data) {
            if (data.error) {
                document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#ff4444">' + data.error + '</div>';
                return;
            }
            if (!data.results || data.results.length === 0) {
                document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#555">No results for &quot;' + q + '&quot;</div>';
                return;
            }
            var html = '<div class="cmd-group"><div class="cmd-group-label">' + data.total + ' file' + (data.total !== 1 ? 's' : '') + (data.truncated ? '+' : '') + ' found</div>';
            data.results.forEach(function(r) {
                var icon = '&#128196;';
                if (['.png','.jpg','.jpeg','.gif','.svg','.webp'].indexOf(r.extension) >= 0) icon = '&#128444;';
                else if (['.py','.js','.ts','.jsx','.tsx','.vue','.php'].indexOf(r.extension) >= 0) icon = '&#128187;';
                else if (['.json','.yml','.yaml','.toml'].indexOf(r.extension) >= 0) icon = '&#9881;';

                html += '<div class="cmd-item cmd-search-result" onclick="location.href=\'/project/' + encodeURIComponent(r.project) + '\'">';
                html += '<div style="display:flex;align-items:center;gap:8px;width:100%">';
                html += '<span>' + icon + '</span>';
                html += '<span style="color:#4fc3f7;font-size:11px;min-width:100px">' + r.project + '</span>';
                html += '<span style="flex:1;color:#ccc">' + r.file + '</span>';
                html += '</div>';

                if (r.matches && r.matches.length > 0) {
                    r.matches.forEach(function(m) {
                        var escaped = m.text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                        var re = new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
                        escaped = escaped.replace(re, '<mark style="background:#4fc3f7;color:#000;padding:0 2px;border-radius:2px">$1</mark>');
                        html += '<div style="font-size:11px;color:#666;padding:2px 0 2px 28px;font-family:monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">';
                        html += '<span style="color:#444;margin-right:6px">L' + m.line + '</span>' + escaped;
                        html += '</div>';
                    });
                }
                html += '</div>';
            });
            html += '</div>';
            document.getElementById('cmdResults').innerHTML = html;
        })
        .catch(function(e) {
            document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#ff4444">Error: ' + e + '</div>';
        });
}

// === Generisches Modal-System ===
var _modalStack = [];

function openModal(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.classList.add('show');
    var idx = _modalStack.indexOf(id);
    if (idx !== -1) _modalStack.splice(idx, 1);
    _modalStack.push(id);
}

function closeModal(id) {
    if (!id) {
        if (_modalStack.length === 0) return;
        id = _modalStack.pop();
    } else {
        var idx = _modalStack.indexOf(id);
        if (idx !== -1) _modalStack.splice(idx, 1);
    }
    var el = document.getElementById(id);
    if (el) el.classList.remove('show');
}

// Overlay-Click: Klick auf modal-overlay (nicht auf Inhalt) schliesst Modal
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal-overlay') && e.target.classList.contains('show')) {
        closeModal(e.target.id);
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName))) {
        e.preventDefault();
        document.getElementById('cmdOverlay').classList.contains('show') ? closeCommandPalette() : openCommandPalette();
    }
    if (e.key === 'Escape') {
        var lightbox = getLightbox();
        if (lightbox && lightbox.classList.contains('show')) { closeLightbox(); e.stopPropagation(); }
        else if (document.getElementById('cmdOverlay') && document.getElementById('cmdOverlay').classList.contains('show')) { closeCommandPalette(); e.stopPropagation(); }
        else if (_modalStack.length > 0) { closeModal(); e.stopPropagation(); }
    }
}, true);

// Global: Sticky thead Position dynamisch berechnen
function updateStickyPositions() {
    var topbar = document.querySelector('.topbar');
    if (!topbar) return;
    var t = topbar.offsetHeight;
    var cumTop = t;
    var stickyEls = ['.news-ticker-bar', '.tab-bar', '.stats-bar', '.stats-row', '.filter-bar'];
    stickyEls.forEach(function(sel) {
        document.querySelectorAll(sel).forEach(function(el) {
            if (el && el.offsetHeight > 0 && el.offsetParent !== null) {
                el.style.top = cumTop + 'px';
                cumTop += el.offsetHeight;
            }
        });
    });
    document.querySelectorAll('thead').forEach(function(thead) {
        var table = thead.closest('table');
        if (!table || table.offsetParent === null) return;
        thead.style.top = cumTop + 'px';
    });
}
window.addEventListener('resize', updateStickyPositions);
setInterval(updateStickyPositions, 500);

// Globale Utility-Funktionen (werden von mehreren Seiten genutzt)
function formatTokens(n) {
    if (!n) return '0';
    if (n >= 1e9) return (n/1e9).toFixed(1) + 'B';
    if (n >= 1e6) return (n/1e6).toFixed(1) + 'M';
    if (n >= 1e3) return (n/1e3).toFixed(1) + 'K';
    return n.toString();
}
function formatDate(iso) {
    if (!iso) return '-';
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function formatDateTime(value) {
    return value ? new Date(value).toLocaleString('en-US') : '-';
}
function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
function formatTimeAgo(isoStr) {
    if (!isoStr) return '-';
    var diff = Math.floor((new Date() - new Date(isoStr)) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + ' min ago';
    if (diff < 86400) return Math.floor(diff / 3600) + ' h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + ' days ago';
    return formatDate(isoStr);
}

// External Links in Sidebar
(async function loadExternalLinks() {
    try {
        var links = await api.get('/api/settings/external-links');
        var section = document.getElementById('externalLinksSection');
        var nav = document.getElementById('externalLinksNav');
        if (!links || !links.length || !section || !nav) return;
        nav.innerHTML = links.map(function(l) {
            return '<a href="' + escapeHtml(l.url) + '" target="_blank" class="nav-item">' +
                '<span class="nav-icon"><i data-lucide="' + escapeHtml(l.icon || 'external-link') + '" class="icon"></i></span>' +
                '<span class="nav-text">' + escapeHtml(l.name) + '</span></a>';
        }).join('');
        section.style.display = '';
        if (typeof lucide !== 'undefined') lucide.createIcons();
    } catch(e) { /* silent */ }
})();
