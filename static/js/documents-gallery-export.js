/**
 * Dokumenten-Browser: Galerie, Tabs, Export, Upload
 * Abhaengig von documents.js (loadedFiles, escapeHtml, setDocStatus, PROJECT_NAME)
 */

// === GALERIE ===

function updateGalleryFromLoaded() {
    var images = loadedFiles.filter(function(f) { return f.type === 'image'; });
    renderDocGallery(images);
}

function renderDocGallery(images) {
    var el = document.getElementById('docGallery');
    if (!el) return;

    if (!images.length) {
        el.innerHTML = '<div class="doc-gallery-empty">' +
            '<div style="font-size:32px;margin-bottom:8px;opacity:0.3"><i data-lucide="image" class="icon" style="width:32px;height:32px;display:inline-block"></i></div>' +
            '<div>No images loaded</div>' +
            '<div style="font-size:11px;margin-top:4px">Click a folder in the browser to load images</div></div>';
        return;
    }

    var html = '<div class="doc-gallery-count">' + images.length + ' image' + (images.length !== 1 ? 's' : '') + ' loaded</div>';
    var show = images.slice(0, 200);
    show.forEach(function(img) {
        var src = '/api/project/' + encodeURIComponent(PROJECT_NAME) + '/document-image/' + encodeURIComponent(img.path);
        html += '<div class="doc-gallery-item" onclick="openLightbox(\'' + src + '\')">' +
            '<img src="' + src + '" alt="' + escapeHtml(img.name) + '" loading="lazy" ' +
            'onload="this.parentElement.classList.add(\'loaded\')" ' +
            'onerror="this.parentElement.classList.add(\'error\')">' +
            '<div class="gallery-label">' + escapeHtml(img.name) + '</div>' +
            '<div class="gallery-loading"><span class="doc-status-spinner"></span></div>' +
            '</div>';
    });
    if (images.length > 200) {
        html += '<div style="padding:20px;text-align:center;color:#666;font-size:12px;grid-column:1/-1">' +
            (images.length - 200) + ' more images not shown</div>';
    }
    el.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

// === DOC-TABS ===

function switchDocTab(tab) {
    document.querySelectorAll('.doc-tab').forEach(function(t) { t.classList.toggle('active', t.dataset.tab === tab); });
    document.querySelectorAll('.doc-tab-content').forEach(function(c) { c.classList.toggle('active', c.id === 'docTab_' + tab); });
}

// === EXPORT ===

function renderExportFileList() {
    var el = document.getElementById('exportFileList');
    if (!el) return;

    if (!loadedFiles.length) {
        el.innerHTML = '<div style="padding:20px;text-align:center;color:#555;font-size:12px">' +
            'No files loaded. Open a folder in the browser to see files.</div>';
        updateExportCount();
        return;
    }

    var html = '';
    loadedFiles.forEach(function(doc) {
        var icon = doc.type === 'image' ? '<i data-lucide="image" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>' : '<i data-lucide="file" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>';
        html += '<div class="export-file-item">' +
            '<input type="checkbox" class="export-check" value="' + escapeHtml(doc.path) + '" checked>' +
            '<span class="file-icon">' + icon + '</span>' +
            '<span class="file-path">' + escapeHtml(doc.path) + '</span>' +
            '<span class="file-size">' + doc.size_human + '</span>' +
            '</div>';
    });
    el.innerHTML = html;
    updateExportCount();
}

function selectAllExport(checked) {
    document.querySelectorAll('.export-check').forEach(function(cb) { cb.checked = checked; });
    updateExportCount();
}

function updateExportCount() {
    var checked = document.querySelectorAll('.export-check:checked').length;
    var total = document.querySelectorAll('.export-check').length;
    var el = document.getElementById('exportCount');
    if (el) el.textContent = checked + ' / ' + total + ' selected';
}

function selectExportFormat(fmt) {
    document.querySelectorAll('.export-format-btn').forEach(function(b) { b.classList.toggle('active', b.dataset.format === fmt); });
}

async function executeExport() {
    var selectedFiles = [];
    document.querySelectorAll('.export-check:checked').forEach(function(cb) { selectedFiles.push(cb.value); });

    var formatBtn = document.querySelector('.export-format-btn.active');
    var format = formatBtn ? formatBtn.dataset.format : 'zip';

    if (!selectedFiles.length) return;

    var exportBtn = document.querySelector('.modal-actions .btn-save');
    if (exportBtn) { exportBtn.textContent = 'Exporting...'; exportBtn.disabled = true; }
    setDocStatus('Exporting ' + selectedFiles.length + ' file' + (selectedFiles.length !== 1 ? 's' : '') + ' as ' + format.toUpperCase() + '...', 'loading');

    try {
        var r = await api.request('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/export-bundle', {
            method: 'POST',
            body: {files: selectedFiles, format: format},
            raw: true
        });

        var blob = await r.blob();
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        var extMap = {zip: '.zip', html: '.html', markdown: '.md', json: '.json'};
        a.href = url;
        a.download = PROJECT_NAME + '-dokumente' + (extMap[format] || '.zip');
        a.click();
        URL.revokeObjectURL(url);
        setDocStatus('Export completed', 'success');
    } catch(e) {
        setDocStatus('Export failed: ' + e, 'error');
    } finally {
        if (exportBtn) { exportBtn.textContent = 'Export'; exportBtn.disabled = false; }
    }
}

document.addEventListener('change', function(e) {
    if (e.target.classList.contains('export-check')) updateExportCount();
});

// === UPLOAD ===

function initUpload() {
    var dropzone = document.getElementById('uploadDropzone');
    var fileInput = document.getElementById('uploadFileInput');
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', function() { fileInput.click(); });

    fileInput.addEventListener('change', function() {
        if (fileInput.files.length > 0) uploadFiles(fileInput.files);
    });

    dropzone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    dropzone.addEventListener('dragleave', function() {
        dropzone.classList.remove('dragover');
    });
    dropzone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) uploadFiles(e.dataTransfer.files);
    });
}

async function uploadFiles(fileList) {
    var files = Array.from(fileList);
    if (files.length === 0) return;
    if (files.length > 20) {
        setDocStatus('Maximum 20 files per upload', 'error');
        return;
    }

    var customDir = document.getElementById('uploadCustomDir').value.trim();
    var selectDir = document.getElementById('uploadTargetDir').value;
    var targetDir = customDir || selectDir;

    var progressEl = document.getElementById('uploadProgress');
    var progressBar = document.getElementById('uploadProgressBar');
    var progressText = document.getElementById('uploadProgressText');
    var resultsEl = document.getElementById('uploadResults');

    progressEl.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = 'Uploading: 0 / ' + files.length + ' file' + (files.length !== 1 ? 's' : '') + '...';
    resultsEl.innerHTML = '';
    setDocStatus('Upload in progress...', 'loading');

    var formData = new FormData();
    formData.append('directory', targetDir);
    files.forEach(function(f) { formData.append('files', f); });

    try {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/project/' + encodeURIComponent(PROJECT_NAME) + '/upload');

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                var pct = Math.round((e.loaded / e.total) * 100);
                progressBar.style.width = pct + '%';
                progressText.textContent = 'Uploading: ' + pct + '%';
            }
        });

        xhr.onload = function() {
            var d = JSON.parse(xhr.responseText);
            progressBar.style.width = '100%';

            var html = '';
            (d.results || []).forEach(function(r) {
                if (r.success) {
                    var icon = r.type === 'image' ? '<i data-lucide="image" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>' : '<i data-lucide="file" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>';
                    html += '<div class="upload-result-item success">' +
                        '<span class="upload-result-icon">' + icon + '</span>' +
                        '<span class="upload-result-name">' + escapeHtml(r.name) + '</span>' +
                        '<span class="upload-result-status" style="color:#4caf50">' + r.size_human + '</span></div>';
                } else {
                    html += '<div class="upload-result-item error">' +
                        '<span class="upload-result-icon"><i data-lucide="x" class="icon" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i></span>' +
                        '<span class="upload-result-name">' + escapeHtml(r.name) + '</span>' +
                        '<span class="upload-result-status" style="color:#ff4444">' + escapeHtml(r.error) + '</span></div>';
                }
            });
            resultsEl.innerHTML = html;

            progressText.textContent = d.uploaded + ' uploaded' + (d.failed > 0 ? ', ' + d.failed + ' failed' : '');
            setDocStatus(d.uploaded + ' file' + (d.uploaded !== 1 ? 's' : '') + ' uploaded to ' + targetDir, 'success');

            // Browser-Baum neu laden
            if (d.uploaded > 0) {
                setTimeout(function() { loadDocuments(); }, 500);
            }

            // File-Input zuruecksetzen
            document.getElementById('uploadFileInput').value = '';
        };

        xhr.onerror = function() {
            progressText.textContent = 'Upload failed';
            setDocStatus('Upload failed', 'error');
        };

        xhr.send(formData);
    } catch(e) {
        progressText.textContent = 'Error: ' + e;
        setDocStatus('Upload failed: ' + e, 'error');
    }
}

// Upload initialisieren wenn DOM bereit
document.addEventListener('DOMContentLoaded', function() { initUpload(); });
