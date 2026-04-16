// Plan-Scan Preview + Exclusions Panel (Sprint sprint-plan-discovery, Commit 5).
// Baum-Rendering, Checkbox-Exclusions, Sync-Now — nutzt api.js + base.js Utils.
(function () {
    'use strict';

    const STATE = {
        preview: null,
        exclusions: [],
        projectFilter: '',
        activeTab: 'preview',
    };

    // -----------------------------------------------------------------------
    // Utils
    // -----------------------------------------------------------------------

    function toast(msg, kind) {
        const el = document.getElementById('planScanToast');
        if (!el) return;
        el.textContent = msg;
        el.className = 'toast show' + (kind ? ' toast-' + kind : '');
        setTimeout(() => { el.className = 'toast'; }, 3500);
    }

    function kindLabel(kind) {
        switch (kind) {
            case 'claude_plans':   return 'Claude Plan';
            case 'project_sprints': return 'Sprint';
            case 'project_plans':  return 'Plan';
            case 'project_docs':   return 'Docs';
            case 'project_root':   return 'Projekt-Root';
            default:               return kind || '?';
        }
    }

    function statusLabel(status) {
        switch (status) {
            case 'new':      return { text: 'Neu',           cls: 'plan-scan-status-new' };
            case 'existing': return { text: 'Bestehend',     cls: 'plan-scan-status-existing' };
            case 'excluded': return { text: 'Ausgeschlossen',cls: 'plan-scan-status-excluded' };
            default:         return { text: status || '?',   cls: '' };
        }
    }

    function shortenPath(path, max) {
        if (!path) return '';
        if (path.length <= max) return path;
        return '…' + path.slice(-Math.max(0, max - 1));
    }

    // -----------------------------------------------------------------------
    // Preview-Loader
    // -----------------------------------------------------------------------

    async function loadPreview(opts) {
        opts = opts || {};
        const loading = document.getElementById('planScanLoading');
        const tree    = document.getElementById('planScanTree');
        const empty   = document.getElementById('planScanEmpty');
        const totals  = document.getElementById('planScanTotals');
        loading.style.display = 'flex';
        tree.style.display = 'none';
        empty.style.display = 'none';
        totals.style.display = 'none';

        let url = '/api/plans/scan-preview';
        const params = [];
        if (STATE.projectFilter) params.push('project=' + encodeURIComponent(STATE.projectFilter));
        if (opts.noCache) params.push('no_cache=1');
        if (params.length) url += '?' + params.join('&');

        try {
            const data = await api.get(url);
            STATE.preview = data;
            renderTotals(data.totals || {});
            renderProjectFilter(data.groups || []);
            renderTree(data.groups || []);
        } catch (err) {
            toast('Preview-Fehler: ' + (err.message || 'Unbekannt'), 'error');
            console.error(err);
        } finally {
            loading.style.display = 'none';
        }
    }

    function renderTotals(t) {
        const el = document.getElementById('planScanTotals');
        document.getElementById('totalTotal').textContent      = t.total      || 0;
        document.getElementById('totalNew').textContent        = t.new        || 0;
        document.getElementById('totalExisting').textContent   = t.existing   || 0;
        document.getElementById('totalExcluded').textContent   = t.excluded   || 0;
        document.getElementById('totalDuplicates').textContent = t.duplicates || 0;
        if (STATE.activeTab === 'preview') el.style.display = 'flex';
    }

    function renderProjectFilter(groups) {
        const sel = document.getElementById('planScanProjectFilter');
        const current = sel.value;
        // Distinct-Projekt-Namen (inkl. claude_plans als __global__)
        const knownProjects = new Set();
        groups.forEach(g => { if (g.project_name) knownProjects.add(g.project_name); });
        const all = Array.from(knownProjects).sort();
        sel.innerHTML = '<option value="">Alle</option>';
        all.forEach(name => {
            const opt = document.createElement('option');
            opt.value = name;
            opt.textContent = name;
            if (name === STATE.projectFilter) opt.selected = true;
            sel.appendChild(opt);
        });
        // Add-Form Projekt-Dropdown mit denselben Projekten versorgen
        const addSel = document.getElementById('exAddProject');
        if (addSel) {
            addSel.innerHTML = '<option value="">Global (alle Projekte)</option>';
            all.forEach(name => {
                const opt = document.createElement('option');
                opt.value = name;
                opt.textContent = name;
                addSel.appendChild(opt);
            });
        }
        if (current) sel.value = current;
    }

    function renderTree(groups) {
        const tree  = document.getElementById('planScanTree');
        const empty = document.getElementById('planScanEmpty');
        tree.innerHTML = '';
        if (!groups.length) {
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';
        tree.style.display = 'block';

        groups.forEach(g => tree.appendChild(renderProjectGroup(g)));
    }

    function renderProjectGroup(group) {
        const wrap = document.createElement('div');
        wrap.className = 'plan-scan-project';
        const title = group.project_name || 'Claude-Plans (global)';
        const header = document.createElement('div');
        header.className = 'plan-scan-project-head';
        header.innerHTML =
            '<div class="plan-scan-project-title"><i data-lucide="folder" class="icon icon-sm"></i> '
            + escapeHtml(title)
            + '</div>'
            + '<div class="plan-scan-project-meta">'
            +   '<span title="Gesamt">' + group.total + '</span>'
            +   ' · <span class="plan-scan-status-new">' + (group.new || 0) + ' neu</span>'
            +   ' · <span class="plan-scan-status-existing">' + (group.existing || 0) + ' bestehend</span>'
            +   ' · <span class="plan-scan-status-excluded">' + (group.excluded || 0) + ' aus</span>'
            + '</div>';
        wrap.appendChild(header);

        (group.kinds || []).forEach(kindGroup => {
            const kindBox = document.createElement('div');
            kindBox.className = 'plan-scan-kind';
            kindBox.innerHTML = '<div class="plan-scan-kind-title">' + escapeHtml(kindLabel(kindGroup.source_kind)) + '</div>';
            (kindGroup.directories || []).forEach(dirGroup => {
                kindBox.appendChild(renderDirGroup(dirGroup, group.project_name));
            });
            wrap.appendChild(kindBox);
        });

        return wrap;
    }

    function renderDirGroup(dir, projectName) {
        const box = document.createElement('div');
        box.className = 'plan-scan-dir';
        const head = document.createElement('div');
        head.className = 'plan-scan-dir-head';
        head.innerHTML =
            '<div class="plan-scan-dir-path" title="' + escapeHtml(dir.directory) + '">'
            +   '<i data-lucide="chevron-down" class="icon icon-xs plan-scan-chevron"></i> '
            +   escapeHtml(shortenPath(dir.directory, 80))
            +   ' <span class="plan-scan-dir-count">' + (dir.files || []).length + '</span>'
            + '</div>'
            + '<button class="btn btn-sm btn-ghost plan-scan-exclude-dir" type="button">Ganzen Ordner ausschliessen</button>';
        head.querySelector('.plan-scan-dir-path').addEventListener('click', () => {
            box.classList.toggle('collapsed');
        });
        head.querySelector('.plan-scan-exclude-dir').addEventListener('click', () =>
            excludeDirectory(dir.directory, projectName));
        box.appendChild(head);

        const list = document.createElement('div');
        list.className = 'plan-scan-file-list';
        (dir.files || []).forEach(file => list.appendChild(renderFileRow(file, projectName)));
        box.appendChild(list);

        return box;
    }

    function renderFileRow(file, projectName) {
        const row = document.createElement('div');
        row.className = 'plan-scan-file plan-scan-file-' + file.status;
        if (file.is_duplicate) row.classList.add('is-duplicate');

        const st = statusLabel(file.status);
        const badges = [
            '<span class="plan-scan-badge plan-scan-badge-kind">' + escapeHtml(kindLabel(file.source_kind)) + '</span>',
            '<span class="plan-scan-badge ' + st.cls + '">' + st.text + '</span>',
        ];
        if (file.is_duplicate) badges.push('<span class="plan-scan-badge plan-scan-badge-dup" title="Content-Duplikat">Duplikat</span>');
        if (file.excluded_by) badges.push('<span class="plan-scan-badge plan-scan-badge-excluded-by" title="' + escapeHtml(file.excluded_by) + '">via ' + escapeHtml(file.excluded_by) + '</span>');

        row.innerHTML =
            '<label class="plan-scan-file-main">'
            +   '<input type="checkbox" class="plan-scan-file-check" '
            +     (file.excluded_by ? 'checked ' : '')
            +     'data-filename="' + escapeHtml(file.filename) + '" '
            +     'data-source-path="' + escapeHtml(file.source_path || '') + '" '
            +     'data-project="' + escapeHtml(projectName || '') + '" />'
            +   '<span class="plan-scan-file-name" title="' + escapeHtml(file.source_path || '') + '">'
            +     escapeHtml(file.filename || '(kein Name)')
            +   '</span>'
            + '</label>'
            + '<div class="plan-scan-file-badges">' + badges.join('') + '</div>';

        const checkbox = row.querySelector('input[type=checkbox]');
        checkbox.addEventListener('change', async () => {
            if (checkbox.checked) {
                await addExclusion({
                    project_name: projectName,
                    path_pattern: deriveFilePattern(file, projectName),
                    scope: 'file',
                    reason: 'UI-Ausschluss ' + file.filename,
                });
            } else if (file.excluded_by) {
                await removeExclusionByPattern(file.excluded_by, projectName);
            }
            loadPreview({ noCache: true });
        });

        return row;
    }

    function deriveFilePattern(file, projectName) {
        if (!file.source_path) return file.filename;
        if (!projectName) return file.filename;
        // relativer Pfad innerhalb /mnt/projects/<project>/
        const needle = '/mnt/projects/' + projectName + '/';
        const idx = file.source_path.indexOf(needle);
        if (idx >= 0) return file.source_path.slice(idx + needle.length);
        return file.filename;
    }

    // -----------------------------------------------------------------------
    // Exclusions-Loader + CRUD
    // -----------------------------------------------------------------------

    async function loadExclusions() {
        const list = document.getElementById('planScanExclusionList');
        list.innerHTML = '<div class="plan-scan-loading"><div class="spinner"></div><div>Lade Exclusions...</div></div>';
        try {
            const data = await api.get('/api/plans/scan-exclusions');
            STATE.exclusions = data.exclusions || [];
            document.getElementById('planScanExclusionsCount').textContent = STATE.exclusions.length;
            renderExclusions();
        } catch (err) {
            toast('Exclusion-Fehler: ' + err.message, 'error');
        }
    }

    function renderExclusions() {
        const list = document.getElementById('planScanExclusionList');
        if (!STATE.exclusions.length) {
            list.innerHTML = '<div class="empty-state-inline">Keine Exclusions aktiv.</div>';
            return;
        }
        const rows = STATE.exclusions.map(ex => {
            const scope = ex.scope === 'folder' ? 'Ordner' : 'Datei';
            const scopeCls = ex.scope === 'folder' ? 'plan-scan-badge-folder' : 'plan-scan-badge-file';
            const proj = ex.project_name || '(global)';
            const when = ex.excluded_at ? formatDate(ex.excluded_at) : '';
            return (
                '<div class="plan-scan-exclusion-row">'
                + '<div class="plan-scan-exclusion-main">'
                +   '<span class="plan-scan-badge ' + scopeCls + '">' + scope + '</span>'
                +   '<span class="plan-scan-exclusion-pattern">' + escapeHtml(ex.path_pattern) + '</span>'
                +   '<span class="plan-scan-exclusion-project">' + escapeHtml(proj) + '</span>'
                + '</div>'
                + '<div class="plan-scan-exclusion-meta">'
                +   (ex.reason ? '<span class="plan-scan-exclusion-reason">' + escapeHtml(ex.reason) + '</span>' : '')
                +   '<span class="plan-scan-exclusion-when">' + escapeHtml(when) + '</span>'
                +   '<button class="btn btn-sm btn-ghost plan-scan-exclusion-rm" data-id="' + ex.id + '">Entfernen</button>'
                + '</div>'
                + '</div>'
            );
        }).join('');
        list.innerHTML = rows;
        list.querySelectorAll('.plan-scan-exclusion-rm').forEach(btn => {
            btn.addEventListener('click', () => removeExclusion(parseInt(btn.dataset.id, 10)));
        });
    }

    async function addExclusion(body) {
        try {
            await api.post('/api/plans/scan-exclusions', body);
            await loadExclusions();
            toast('Exclusion gespeichert', 'ok');
        } catch (err) {
            toast('Fehler beim Speichern: ' + err.message, 'error');
        }
    }

    async function removeExclusion(id) {
        try {
            await api.del('/api/plans/scan-exclusions/' + id);
            await loadExclusions();
            await loadPreview({ noCache: true });
            toast('Exclusion entfernt', 'ok');
        } catch (err) {
            toast('Fehler: ' + err.message, 'error');
        }
    }

    async function removeExclusionByPattern(pattern, projectName) {
        const match = STATE.exclusions.find(ex =>
            ex.path_pattern === pattern &&
            (ex.project_name || null) === (projectName || null));
        if (match) await removeExclusion(match.id);
    }

    async function excludeDirectory(dir, projectName) {
        let pattern;
        if (!projectName) {
            toast('Claude-Plans lassen sich nur dateiweise ausschliessen.', 'error');
            return;
        }
        const needle = '/mnt/projects/' + projectName + '/';
        const idx = dir.indexOf(needle);
        if (idx >= 0) pattern = dir.slice(idx + needle.length) + '/**';
        else pattern = dir + '/**';
        await addExclusion({
            project_name: projectName,
            path_pattern: pattern,
            scope: 'folder',
            reason: 'UI-Ausschluss Ordner',
        });
        await loadPreview({ noCache: true });
    }

    // -----------------------------------------------------------------------
    // Sync-Now
    // -----------------------------------------------------------------------

    async function syncNow(btn) {
        btn.disabled = true;
        const originalHtml = btn.innerHTML;
        btn.innerHTML = '<div class="spinner spinner-sm"></div> Scanne...';
        try {
            const result = await api.post('/api/plans/sync-now', {});
            const s = result.stats || {};
            if (s.skipped_reason) {
                toast('Scan ausgesetzt: ' + s.skipped_reason, 'error');
            } else {
                toast(
                    'Import: ' + (s.inserted || 0) + ' neu · '
                    + (s.updated || 0) + ' geaendert · '
                    + (s.migrated || 0) + ' migriert · '
                    + (s.skipped || 0) + ' skipped · '
                    + (s.duration_ms || 0) + ' ms',
                    'ok'
                );
                await loadPreview({ noCache: true });
            }
        } catch (err) {
            toast('Sync-Fehler: ' + err.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            if (window.lucide) window.lucide.createIcons();
        }
    }

    // -----------------------------------------------------------------------
    // Tab-Handling
    // -----------------------------------------------------------------------

    function switchTab(tab) {
        STATE.activeTab = tab;
        document.querySelectorAll('.plan-scan-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        document.querySelectorAll('[data-tab-pane]').forEach(pane => {
            pane.style.display = pane.dataset.tabPane === tab ? 'block' : 'none';
        });
        document.querySelectorAll('[data-tab-only]').forEach(el => {
            el.style.display = el.dataset.tabOnly === tab ? '' : 'none';
        });
        if (tab === 'exclusions') loadExclusions();
    }

    // -----------------------------------------------------------------------
    // Init
    // -----------------------------------------------------------------------

    function init() {
        document.querySelectorAll('.plan-scan-tab').forEach(btn => {
            btn.addEventListener('click', () => switchTab(btn.dataset.tab));
        });
        document.getElementById('planScanProjectFilter').addEventListener('change', (ev) => {
            STATE.projectFilter = ev.target.value || '';
            loadPreview({ noCache: true });
        });
        document.getElementById('planScanRefreshBtn').addEventListener('click', () => loadPreview({ noCache: true }));
        document.getElementById('planScanSyncBtn').addEventListener('click', (ev) => syncNow(ev.currentTarget));
        document.getElementById('exAddBtn').addEventListener('click', async () => {
            const project = document.getElementById('exAddProject').value;
            const scope   = document.getElementById('exAddScope').value;
            const pattern = document.getElementById('exAddPattern').value.trim();
            const reason  = document.getElementById('exAddReason').value.trim();
            if (!pattern) { toast('Pattern erforderlich', 'error'); return; }
            await addExclusion({
                project_name: project || null,
                path_pattern: pattern,
                scope: scope,
                reason: reason || null,
            });
            document.getElementById('exAddPattern').value = '';
            document.getElementById('exAddReason').value  = '';
        });
        loadPreview();
        loadExclusions();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
