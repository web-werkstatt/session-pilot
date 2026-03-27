/**
 * Dokumenten-Browser: Lazy-Loading Baum, Viewer, Galerie, Export
 * Laedt nur das aktuelle Verzeichnis - Unterordner erst bei Klick.
 */

let activeDocPath = null;
let docEditorMDE = null;
let loadedFiles = [];

// === STATUS-LEISTE ===

function setDocStatus(msg, type) {
    // type: 'loading', 'success', 'info', 'error'
    var bar = document.getElementById('docStatusBar');
    if (!bar) return;
    var colors = {loading: '#4fc3f7', success: '#4caf50', info: '#888', error: '#ff4444'};
    var icons = {loading: '<span class="doc-status-spinner"></span>', success: '<i data-lucide="check" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>', info: '<i data-lucide="info" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>', error: '<i data-lucide="x" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>'};
    bar.innerHTML = '<span style="color:' + (colors[type] || '#888') + '">' + (icons[type] || '') + ' ' + msg + '</span>';
    bar.style.display = 'flex';
    if (typeof lucide !== 'undefined') lucide.createIcons();
    if (type === 'success') {
        setTimeout(function() { bar.style.display = 'none'; }, 2500);
    }
}

function hideDocStatus() {
    var bar = document.getElementById('docStatusBar');
    if (bar) bar.style.display = 'none';
}

// === LADEN ===

async function loadDocuments() {
    setDocStatus('Verzeichnis wird gelesen...', 'loading');
    await loadDirectory('.');
    setDocStatus('Bereit', 'success');
}

async function loadDirectory(dir) {
    try {
        var r = await fetch('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/documents?dir=' + encodeURIComponent(dir));
        var d = await r.json();
        if (d.error) {
            setDocStatus('Fehler: ' + d.error, 'error');
            return;
        }

        if (dir === '.') {
            renderDocStats(d.counts);
            var body = document.getElementById('docTreeBody');
            if (body) body.innerHTML = '';
            loadedFiles = d.files || [];
        }

        renderDirNode(dir, d.files, d.subdirs);
        updateGalleryFromLoaded();

    } catch(e) {
        setDocStatus('Laden fehlgeschlagen: ' + e, 'error');
    }
}

// === STATS ===

function renderDocStats(counts) {
    var el = document.getElementById('docStatsBar');
    if (!el || !counts) return;
    el.innerHTML =
        '<div class="doc-stat"><span class="doc-stat-value">' + counts.files + '</span> Dateien</div>' +
        '<div class="doc-stat"><span class="doc-stat-value">' + counts.documents + '</span> Dokumente</div>' +
        '<div class="doc-stat"><span class="doc-stat-value">' + counts.images + '</span> Bilder</div>' +
        '<div class="doc-stat"><span class="doc-stat-value">' + counts.subdirs + '</span> Unterordner</div>';
}

// === BAUM (Lazy) ===

function renderDirNode(dir, files, subdirs) {
    var body = document.getElementById('docTreeBody');
    if (!body) return;

    var dirLabel = dir === '.' ? 'Root' : dir.split('/').pop();
    var indent = dir === '.' ? 0 : dir.split('/').length;

    var dirEl = document.createElement('div');
    dirEl.className = 'doc-dir';
    dirEl.dataset.dir = dir;

    var labelEl = document.createElement('div');
    labelEl.className = 'doc-dir-label';
    labelEl.style.paddingLeft = (14 + indent * 12) + 'px';
    labelEl.innerHTML =
        '<span class="dir-arrow">&#9660;</span>' +
        '<span><i data-lucide="folder" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> ' + dirLabel + '</span>' +
        '<span style="margin-left:auto;color:#444;font-size:10px">' + (files.length + subdirs.length) + '</span>';
    labelEl.onclick = function() { dirEl.classList.toggle('collapsed'); };
    dirEl.appendChild(labelEl);

    var filesEl = document.createElement('div');
    filesEl.className = 'doc-dir-files';

    subdirs.forEach(function(sub) {
        var subEl = document.createElement('div');
        subEl.className = 'doc-dir';
        subEl.dataset.dir = sub.path;

        var subLabel = document.createElement('div');
        subLabel.className = 'doc-dir-label';
        subLabel.style.paddingLeft = (14 + (indent + 1) * 12) + 'px';
        subLabel.innerHTML =
            '<span class="dir-arrow" style="transform:rotate(-90deg)">&#9660;</span>' +
            '<span><i data-lucide="folder" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> ' + sub.name + '</span>' +
            '<span style="margin-left:auto;color:#444;font-size:10px">...</span>';
        subLabel.onclick = function(e) {
            e.stopPropagation();
            expandSubdir(subEl, sub.path, indent + 1);
        };
        subEl.appendChild(subLabel);
        filesEl.appendChild(subEl);
    });

    files.forEach(function(f) {
        var icon = f.type === 'image' ? '<i data-lucide="image" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>' : '<i data-lucide="file" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>';
        var fileEl = document.createElement('div');
        fileEl.className = 'doc-file';
        fileEl.dataset.path = f.path;
        fileEl.style.paddingLeft = (28 + indent * 12) + 'px';
        fileEl.innerHTML =
            '<span class="doc-file-icon">' + icon + '</span>' +
            '<span class="doc-file-name" title="' + f.path + '">' + f.name + '</span>' +
            '<span class="doc-file-size">' + f.size_human + '</span>';
        fileEl.onclick = function() { openDocument(f.path); };
        filesEl.appendChild(fileEl);
    });

    dirEl.appendChild(filesEl);

    if (dir === '.') {
        body.appendChild(dirEl);
    } else {
        var parent = body.querySelector('[data-dir="' + CSS.escape(dir) + '"]');
        if (parent) parent.replaceWith(dirEl);
    }

    // Lucide Icons rendern nach DOM-Update
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

async function expandSubdir(el, dirPath, indent) {
    if (el.dataset.loaded === 'true') {
        el.classList.toggle('collapsed');
        return;
    }

    var label = el.querySelector('.doc-dir-label');
    var countSpan = label.querySelector('span:last-child');
    var arrow = label.querySelector('.dir-arrow');

    // Lade-Animation
    countSpan.innerHTML = '<span class="doc-status-spinner" style="width:12px;height:12px;border-width:2px"></span>';
    setDocStatus('Lade ' + dirPath + ' ...', 'loading');

    try {
        var r = await fetch('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/documents?dir=' + encodeURIComponent(dirPath));
        var d = await r.json();
        if (d.error) {
            countSpan.textContent = '!';
            setDocStatus('Fehler: ' + d.error, 'error');
            return;
        }

        el.dataset.loaded = 'true';
        arrow.style.transform = '';
        countSpan.textContent = d.counts.files + d.counts.subdirs;

        var filesEl = document.createElement('div');
        filesEl.className = 'doc-dir-files';

        d.subdirs.forEach(function(sub) {
            var subEl = document.createElement('div');
            subEl.className = 'doc-dir';
            subEl.dataset.dir = sub.path;

            var subLabel = document.createElement('div');
            subLabel.className = 'doc-dir-label';
            subLabel.style.paddingLeft = (14 + (indent + 1) * 12) + 'px';
            subLabel.innerHTML =
                '<span class="dir-arrow" style="transform:rotate(-90deg)">&#9660;</span>' +
                '<span><i data-lucide="folder" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i> ' + sub.name + '</span>' +
                '<span style="margin-left:auto;color:#444;font-size:10px">...</span>';
            subLabel.onclick = function(e) {
                e.stopPropagation();
                expandSubdir(subEl, sub.path, indent + 1);
            };
            subEl.appendChild(subLabel);
            filesEl.appendChild(subEl);
        });

        d.files.forEach(function(f) {
            var icon = f.type === 'image' ? '<i data-lucide="image" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>' : '<i data-lucide="file" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>';
            var fileEl = document.createElement('div');
            fileEl.className = 'doc-file';
            fileEl.dataset.path = f.path;
            fileEl.style.paddingLeft = (28 + (indent + 1) * 12) + 'px';
            fileEl.innerHTML =
                '<span class="doc-file-icon">' + icon + '</span>' +
                '<span class="doc-file-name" title="' + f.path + '">' + f.name + '</span>' +
                '<span class="doc-file-size">' + f.size_human + '</span>';
            fileEl.onclick = function() { openDocument(f.path); };
            filesEl.appendChild(fileEl);
        });

        el.appendChild(filesEl);
        loadedFiles = loadedFiles.concat(d.files);
        updateGalleryFromLoaded();
        label.onclick = function() { el.classList.toggle('collapsed'); };
        // Lucide Icons rendern nach DOM-Update
        if (typeof lucide !== 'undefined') lucide.createIcons();

        var newImgs = d.files.filter(function(f) { return f.type === 'image'; }).length;
        setDocStatus(d.counts.files + ' Dateien, ' + d.counts.subdirs + ' Ordner geladen' + (newImgs ? ' (+' + newImgs + ' Bilder in Galerie)' : ''), 'success');

    } catch(e) {
        countSpan.textContent = '!';
        setDocStatus('Laden fehlgeschlagen: ' + e, 'error');
    }
}

function filterDocTree() {
    var q = document.getElementById('docTreeSearch').value.toLowerCase().trim();
    var allFiles = document.querySelectorAll('.doc-file');
    var allDirs = document.querySelectorAll('.doc-dir');

    if (!q) {
        allFiles.forEach(function(f) { f.style.display = ''; });
        allDirs.forEach(function(d) { d.style.display = ''; d.classList.remove('collapsed'); });
        return;
    }

    allFiles.forEach(function(f) {
        var name = (f.dataset.path || '').toLowerCase();
        f.style.display = name.includes(q) ? '' : 'none';
    });

    allDirs.forEach(function(d) {
        var visibleFiles = d.querySelectorAll('.doc-file:not([style*="display: none"])');
        var visibleSubdirs = d.querySelectorAll('.doc-dir:not([style*="display: none"])');
        if (visibleFiles.length === 0 && visibleSubdirs.length === 0 && d.querySelector('.doc-dir-files')) {
            d.style.display = 'none';
        } else {
            d.style.display = '';
            d.classList.remove('collapsed');
        }
    });
}

// === VIEWER ===

async function openDocument(path) {
    activeDocPath = path;

    document.querySelectorAll('.doc-file').forEach(function(el) {
        el.classList.toggle('active', el.dataset.path === path);
    });

    var viewer = document.getElementById('docViewerBody');
    var pathEl = document.getElementById('docViewerPath');
    var actionsEl = document.getElementById('docViewerActions');
    if (!viewer) return;

    pathEl.textContent = path;
    viewer.innerHTML = '<div class="doc-viewer-empty"><div class="spinner"></div> Lade ' + escapeHtml(path) + '...</div>';

    if (docEditorMDE) {
        try { docEditorMDE.toTextArea(); } catch(e) { /* CodeMirror cleanup */ }
        docEditorMDE = null;
    }

    try {
        var r = await fetch('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/document/' + encodeURIComponent(path));
        var d = await r.json();

        if (d.type === 'document') {
            actionsEl.innerHTML =
                '<button class="doc-viewer-btn" id="docEditBtn" onclick="toggleDocEdit()">&#9998; Bearbeiten</button>' +
                '<button class="doc-viewer-btn" id="docSaveBtn" onclick="saveDocContent()" style="display:none">&#128190; Speichern</button>' +
                '<button class="doc-viewer-btn" id="docCancelBtn" onclick="cancelDocEdit()" style="display:none">Abbrechen</button>' +
                '<span id="docEditStatus" style="color:#666;font-size:11px"></span>';

            if (d.html) {
                viewer.innerHTML = '<div class="doc-rendered">' + d.html + '</div>' +
                    '<div id="docEditorWrap" style="display:none"><textarea id="docEditorArea">' + escapeHtml(d.content) + '</textarea></div>';
            } else {
                viewer.innerHTML = '<div class="doc-raw">' + escapeHtml(d.content) + '</div>' +
                    '<div id="docEditorWrap" style="display:none"><textarea id="docEditorArea">' + escapeHtml(d.content) + '</textarea></div>';
            }
        } else if (d.type === 'image') {
            actionsEl.innerHTML = '';
            viewer.innerHTML = '<div class="doc-image-preview">' +
                '<img src="' + d.data_url + '" alt="' + escapeHtml(path) + '" onclick="openLightbox(this.src)">' +
                '</div>';
        }
    } catch(e) {
        viewer.innerHTML = '<div class="doc-viewer-empty" style="color:#ff6666">Fehler: ' + e + '</div>';
    }
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleDocEdit() {
    var rendered = document.getElementById('docViewerBody').querySelector('.doc-rendered, .doc-raw');
    var editorWrap = document.getElementById('docEditorWrap');
    if (!editorWrap) return;

    if (rendered) rendered.style.display = 'none';
    editorWrap.style.display = 'block';
    document.getElementById('docEditBtn').style.display = 'none';
    document.getElementById('docSaveBtn').style.display = 'inline-block';
    document.getElementById('docCancelBtn').style.display = 'inline-block';

    if (!docEditorMDE) {
        docEditorMDE = new EasyMDE({
            element: document.getElementById('docEditorArea'),
            spellChecker: false,
            autofocus: true,
            minHeight: '350px',
            status: ['lines', 'words'],
            toolbar: [
                'bold', 'italic', 'heading', '|',
                'code', 'quote', 'unordered-list', 'ordered-list', '|',
                'link', 'image', 'table', 'horizontal-rule', '|',
                'preview', 'side-by-side', 'fullscreen', '|', 'guide'
            ]
        });
    }
}

async function saveDocContent() {
    if (!activeDocPath || !docEditorMDE) return;
    var status = document.getElementById('docEditStatus');
    status.textContent = 'Speichern...';
    status.style.color = '#888';

    try {
        var r = await fetch('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/document/' + encodeURIComponent(activeDocPath), {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: docEditorMDE.value()})
        });
        var d = await r.json();
        if (d.success) {
            status.textContent = 'Gespeichert';
            status.style.color = '#4caf50';
            cancelDocEdit();
            openDocument(activeDocPath);
        } else {
            status.textContent = d.error;
            status.style.color = '#ff4444';
        }
    } catch(e) {
        status.textContent = 'Fehler: ' + e;
        status.style.color = '#ff4444';
    }
}

function cancelDocEdit() {
    if (docEditorMDE) {
        try { docEditorMDE.toTextArea(); } catch(e) { /* CodeMirror cleanup */ }
        docEditorMDE = null;
    }
    var rendered = document.getElementById('docViewerBody').querySelector('.doc-rendered, .doc-raw');
    var editorWrap = document.getElementById('docEditorWrap');
    if (rendered) rendered.style.display = '';
    if (editorWrap) editorWrap.style.display = 'none';

    var editBtn = document.getElementById('docEditBtn');
    var saveBtn = document.getElementById('docSaveBtn');
    var cancelBtn = document.getElementById('docCancelBtn');
    if (editBtn) editBtn.style.display = 'inline-block';
    if (saveBtn) saveBtn.style.display = 'none';
    if (cancelBtn) cancelBtn.style.display = 'none';
    var status = document.getElementById('docEditStatus');
    if (status) status.textContent = '';
}

