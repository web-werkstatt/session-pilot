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
    lbIndex = collectLightboxImages(src);
    showLightboxImage();
    document.getElementById('lightbox').classList.add('show');
}

function showLightboxImage() {
    if (lbImages.length === 0) return;
    var item = lbImages[lbIndex];
    document.getElementById('lightboxImg').src = item.src;
    var info = document.getElementById('lbInfo');
    var counter = document.getElementById('lbCounter');
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
    document.getElementById('lightbox').classList.remove('show');
    document.getElementById('lightboxImg').src = '';
}

document.addEventListener('click', function(e) {
    if (e.target.tagName === 'IMG' && !e.target.closest('.lightbox') && !e.target.closest('.sidebar')) {
        e.preventDefault(); e.stopPropagation(); openLightbox(e.target.src);
    }
}, true);

document.addEventListener('keydown', function(e) {
    if (!document.getElementById('lightbox').classList.contains('show')) return;
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
        '<div class="cmd-group"><div class="cmd-group-label">Schnellzugriff</div>' +
        '<div class="cmd-item" onclick="location.href=\'/\'">&#128202; Dashboard</div>' +
        '<div class="cmd-item" onclick="location.href=\'/sessions\'">&#129302; Claude Sessions</div>' +
        '<div class="cmd-item" onclick="location.href=\'/sessions/analysis\'">&#128200; Session-Analyse</div>' +
        '<div class="cmd-item" onclick="location.href=\'/containers\'">&#128051; Container</div>' +
        '<div class="cmd-item" onclick="location.href=\'/dependencies\'">&#128279; Abh\u00e4ngigkeiten</div>' +
        '<div class="cmd-item" onclick="location.href=\'/vorlagen\'">&#128230; Vorlagen</div>' +
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

    document.getElementById('cmdTabs').style.display = 'flex';

    if (cmdActiveTab === 'fulltext') {
        clearTimeout(cmdSearchTimer);
        cmdSearchTimer = setTimeout(function() { doFulltextSearch(q); }, 400);
        return;
    }

    doProjectSearch(q);
}

function doProjectSearch(q) {
    fetch('/api/projects/search?q=' + encodeURIComponent(q) + '&limit=8')
        .then(function(r) { return r.json(); })
        .then(function(results) {
            var html = '';
            if (results.length > 0) {
                html += '<div class="cmd-group"><div class="cmd-group-label">Projekte</div>';
                results.forEach(function(p) {
                    html += '<div class="cmd-item" onclick="location.href=\'/project/' + encodeURIComponent(p.name) + '\'">&#128193; ' + p.name + ' <span style="color:#666;font-size:11px;margin-left:8px">' + (p.description || '') + '</span></div>';
                });
                html += '</div>';
            }
            var statics = [
                {label:'Dashboard', icon:'&#128202;', url:'/'},
                {label:'Claude Sessions', icon:'&#129302;', url:'/sessions'},
                {label:'Session-Analyse', icon:'&#128200;', url:'/sessions/analysis'},
                {label:'Container', icon:'&#128051;', url:'/containers'},
                {label:'Abh\u00e4ngigkeiten', icon:'&#128279;', url:'/dependencies'},
                {label:'Vorlagen', icon:'&#128230;', url:'/vorlagen'},
                {label:'News', icon:'&#128240;', url:'/news'},
            ].filter(function(s) { return s.label.toLowerCase().includes(q); });
            if (statics.length > 0) {
                html += '<div class="cmd-group"><div class="cmd-group-label">Seiten</div>';
                statics.forEach(function(s) { html += '<div class="cmd-item" onclick="location.href=\'' + s.url + '\'">' + s.icon + ' ' + s.label + '</div>'; });
                html += '</div>';
            }
            if (!html) html = '<div style="padding:20px;text-align:center;color:#555">Keine Ergebnisse</div>';
            document.getElementById('cmdResults').innerHTML = html;
        });
}

function doFulltextSearch(q) {
    if (q.length < 2) {
        document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#555">Mindestens 2 Zeichen eingeben</div>';
        return;
    }
    document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#555"><span class="doc-status-spinner" style="display:inline-block;width:16px;height:16px;border-width:2px;vertical-align:middle;margin-right:8px"></span>Suche in allen Projekten...</div>';

    fetch('/api/search?q=' + encodeURIComponent(q) + '&limit=30')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) {
                document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#ff4444">' + data.error + '</div>';
                return;
            }
            if (!data.results || data.results.length === 0) {
                document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#555">Keine Treffer fuer &quot;' + q + '&quot;</div>';
                return;
            }
            var html = '<div class="cmd-group"><div class="cmd-group-label">' + data.total + ' Dateien' + (data.truncated ? '+' : '') + ' gefunden</div>';
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
            document.getElementById('cmdResults').innerHTML = '<div style="padding:20px;text-align:center;color:#ff4444">Fehler: ' + e + '</div>';
        });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName))) {
        e.preventDefault();
        document.getElementById('cmdOverlay').classList.contains('show') ? closeCommandPalette() : openCommandPalette();
    }
    if (e.key === 'Escape') {
        if (document.getElementById('lightbox').classList.contains('show')) { closeLightbox(); e.stopPropagation(); }
        else if (document.getElementById('cmdOverlay').classList.contains('show')) { closeCommandPalette(); e.stopPropagation(); }
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
