    let vorlagenData = [];

    function loadVorlagen() {
        fetch('/api/vorlagen')
            .then(r => r.json())
            .then(data => {
                vorlagenData = data.vorlagen;
                document.getElementById('loading').style.display = 'none';

                if (vorlagenData.length === 0) {
                    document.getElementById('emptyState').style.display = 'block';
                } else {
                    document.getElementById('vorlagenGrid').style.display = 'grid';
                    renderVorlagen(vorlagenData);
                }
            })
            .catch(err => {
                document.getElementById('loading').innerHTML = 'Fehler: ' + err;
            });
    }

    function renderVorlagen(vorlagen) {
        const grid = document.getElementById('vorlagenGrid');

        const icons = {
            'news-ticker': '📰',
            'dark-theme_special': '🎨',
            'default': '📦'
        };

        let html = '';
        vorlagen.forEach(v => {
            const icon = icons[v.name] || icons['default'];
            const description = v.readme
                ? v.readme.split('\n').slice(0, 3).join(' ').substring(0, 150) + '...'
                : 'Keine Beschreibung verfügbar';

            html += `
                <div class="vorlage-card">
                    <div class="vorlage-header">
                        <span class="vorlage-icon">${icon}</span>
                        <span class="vorlage-title">${v.name}</span>
                    </div>
                    <div class="vorlage-body">
                        <p class="vorlage-description">${description}</p>

                        <div class="vorlage-files">
                            <h4>Dateien</h4>
                            <div class="file-list">
                                ${v.files.map(f => {
                                    const ext = f.split('.').pop();
                                    return `<span class="file-tag ${ext}">${f}</span>`;
                                }).join('')}
                            </div>
                        </div>

                        <div class="vorlage-actions">
                            ${v.preview ? `<button class="action-btn primary" onclick="openPreview('${v.name}', '${v.preview}')">👁 Vorschau</button>` : ''}
                            <button class="action-btn secondary" onclick="showCode('${v.name}')">📄 Code anzeigen</button>
                            <button class="action-btn copy" onclick="copyPath('${v.path}')">📋 Pfad kopieren</button>
                        </div>

                        <div class="path-display">
                            <span>${v.path}</span>
                            <span class="copy-icon" onclick="copyPath('${v.path}')">📋</span>
                        </div>
                    </div>
                </div>
            `;
        });
        grid.innerHTML = html;
    }

    function openPreview(name, file) {
        window.open(`/mnt/projects/vorlagen/${name}/${file}`, '_blank');
    }

    function showCode(name) {
        const vorlage = vorlagenData.find(v => v.name === name);
        if (!vorlage) return;

        document.getElementById('modalTitle').textContent = name + ' - Code';

        let html = '';
        vorlage.files.forEach(file => {
            const ext = file.split('.').pop();
            html += `
                <div class="code-block">
                    <div class="code-header">
                        <span>${file}</span>
                        <button class="action-btn copy" onclick="copyFile('${vorlage.path}/${file}')" style="padding:5px 10px;font-size:11px;">
                            📋 Kopieren
                        </button>
                    </div>
                    <div class="code-content" id="code-${file.replace('.', '-')}">
                        Lade...
                    </div>
                </div>
            `;
        });

        document.getElementById('modalBody').innerHTML = html;
        document.getElementById('codeModal').classList.add('show');

        // Dateien laden (simuliert - in echt brauchst du eine API)
        if (vorlage.readme) {
            const readmeEl = document.getElementById('code-README-md');
            if (readmeEl) readmeEl.textContent = vorlage.readme;
        }
    }

    function closeModal() {
        document.getElementById('codeModal').classList.remove('show');
    }

    function copyPath(path) {
        navigator.clipboard.writeText(path).then(() => {
            showToast('Pfad kopiert: ' + path);
        });
    }

    function copyFile(path) {
        navigator.clipboard.writeText(path).then(() => {
            showToast('Dateipfad kopiert!');
        });
    }

    function showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }

    // Laden
    loadVorlagen();
