/**
 * Copilot Workspace — AI-native Work OS
 * Split View: Board links, permanent Panel rechts mit Tabs
 */

var BOARD_COLUMNS = [
    { status: 'todo',         label: 'Todo',          emoji: '📝', dot: '#64748b', description: 'Noch nicht gestartet', emptyText: 'Keine offenen Marker' },
    { status: 'in_progress',  label: 'Generating',    emoji: '⚡', dot: '#3b82f6', description: 'AI arbeitet', emptyText: 'Keine laufenden Marker' },
    { status: 'done',         label: 'Done',          emoji: '✅', dot: '#22c55e', description: 'Abgeschlossen', emptyText: 'Noch nichts erledigt' },
    { status: 'blocked',      label: 'Blocked',       emoji: '🚧', dot: '#ef4444', description: 'Wartet auf Klaerung', emptyText: 'Keine blockierten Marker' },
];

var allSections = [];
var _currentSection = null;
var _currentThreadId = null;
var _pendingImages = [];
var _planInfo = null;
var _activePanelTab = 'chat';
var _currentProjectId = null;
var _currentMarkerPlanId = null;
var _planSections = [];
var _currentPlanSectionId = null;

document.addEventListener('DOMContentLoaded', function() {
    _loadPlanInfo()
        .finally(function() {
            _loadSections();
            _loadPlanSwitcher();
        });
    document.addEventListener('click', function(e) {
        var dd = document.getElementById('planSwitcherDD');
        var btn = document.getElementById('planSwitcherBtn');
        if (dd && dd.style.display !== 'none' && !dd.contains(e.target) && !btn.contains(e.target)) {
            dd.style.display = 'none';
        }
    });
});

/* === Plan Info === */
function _loadPlanInfo() {
    return api.get('/api/plans/' + PLAN_ID)
        .then(function(plan) {
            _planInfo = plan;
            _currentProjectId = plan.project_name || null;
            _currentMarkerPlanId = _extractMarkerPlanId(plan) || String(PLAN_ID);
            _planSections = _derivePlanSections(plan);
            var label = plan.title || 'Plan #' + PLAN_ID;
            document.getElementById('planSwitcherLabel').textContent = 'Plan switch';
            document.getElementById('currentPlanTitle').textContent = label;
            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, '', _buildCopilotUrl(PLAN_ID, label));
            }
        })
        .catch(function() {
            _currentMarkerPlanId = String(PLAN_ID);
            _planSections = [];
            document.getElementById('planSwitcherLabel').textContent = 'Plan switch';
            document.getElementById('currentPlanTitle').textContent = 'Plan #' + PLAN_ID;
        });
}

/* === Plan Switcher === */
function _loadPlanSwitcher() {
    api.get('/api/copilot/stats')
        .then(function(data) {
            var plans = data.active_plans || [];
            var dd = document.getElementById('planSwitcherDD');
            var html = '';
            plans.forEach(function(p) {
                var cls = p.id === PLAN_ID ? ' active' : '';
                html += '<button class="copilot-plan-switch-item' + cls + '" onclick="switchPlan(' + p.id + ', \'' + _escapeJsString(p.title || ('Plan ' + p.id)) + '\')">'
                    + escapeHtml(p.title || 'Plan #' + p.id)
                    + '<small>' + escapeHtml(p.project_name || '') + ' &middot; ' + (p.status || '') + '</small>'
                    + '</button>';
            });
            if (plans.length > 0) {
                html += '<div class="copilot-plan-switch-divider"></div>';
            }
            html += '<button class="copilot-plan-switch-item" onclick="window.location.href=\'/plans\'">Show all plans &rarr;</button>';
            dd.innerHTML = html;
        })
        .catch(function() {});
}

function togglePlanSwitcher() {
    var dd = document.getElementById('planSwitcherDD');
    dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
}

function switchPlan(planId, planTitle) {
    window.location.href = _buildCopilotUrl(planId, planTitle);
}

/* === Sections laden === */
function _loadSections() {
    api.get(_buildMarkerApiUrl())
        .then(function(data) {
            allSections = _filterMarkersForWorkspace((data.markers || []).map(_normalizeMarker));
            document.getElementById('loading').style.display = 'none';
            if (allSections.length === 0) {
                document.getElementById('sectionsBoard').style.display = 'none';
                document.getElementById('emptyState').style.display = 'block';
            } else {
                document.getElementById('emptyState').style.display = 'none';
                _renderBoard();
            }
            _renderSprintSections();
            _renderProgress();
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function() {
            document.getElementById('loading').innerHTML = '<div class="error">Fehler beim Laden</div>';
        });
}

function _filterMarkersForWorkspace(markers) {
    var items = Array.isArray(markers) ? markers.slice() : [];
    if (!_planSections.length || !_planInfo) return items;

    var planTitle = _normalizeCompareText(_planInfo.title || '');
    return items.filter(function(marker) {
        var hasStructureTag = !!((marker.sprint_tag || '').trim() || (marker.spec_tag || '').trim());
        if (hasStructureTag) return true;

        var markerTitle = _normalizeCompareText(marker.titel || '');
        var markerPlanId = String(marker.plan_id || '');
        var currentPlanId = String(_currentMarkerPlanId || PLAN_ID || '');
        var looksLikeGenericPlanMarker = markerPlanId === currentPlanId && markerTitle && planTitle && markerTitle === planTitle;
        return !looksLikeGenericPlanMarker;
    });
}

/* === Progress Bar === */
function _renderProgress() {
    var total = allSections.length;
    var done = allSections.filter(function(s) { return s.status === 'done'; }).length;
    var blocked = allSections.filter(function(s) { return s.status === 'blocked'; }).length;
    var pct = total > 0 ? Math.round((done / total) * 100) : 0;

    document.getElementById('progressBar').style.width = pct + '%';
    document.getElementById('progressPercent').textContent = pct + '%';
    document.getElementById('progressTasks').textContent = total + ' Tasks';
    document.getElementById('progressDone').textContent = done + ' Done';
    document.getElementById('progressReview').textContent = blocked + ' Blocked';
}

/* === Board rendern === */
function _renderBoard() {
    var board = document.getElementById('sectionsBoard');
    board.style.display = 'flex';

    var grouped = {};
    BOARD_COLUMNS.forEach(function(col) { grouped[col.status] = []; });
    allSections.forEach(function(sec) {
        var st = sec.status || 'todo';
        if (grouped[st]) grouped[st].push(sec);
        else grouped.todo.push(sec);
    });

    var html = '';
    BOARD_COLUMNS.forEach(function(col) {
        var items = grouped[col.status];
        html += '<div class="board-column" data-status="' + col.status + '">';
        html += '<div class="board-column-header">';
        html += '<span class="column-emoji">' + col.emoji + '</span>';
        html += '<span class="column-label">' + col.label + '</span>';
        html += '<span class="board-count">' + items.length + '</span>';
        html += '</div>';
        html += '<div class="column-description">' + col.description + '</div>';
        html += '<div class="board-column-body" data-status="' + col.status + '">';
        if (items.length === 0) {
            html += '<div class="column-empty">' + col.emptyText + '</div>';
        }
        items.forEach(function(sec) {
            html += _buildCard(sec);
        });
        html += '</div></div>';
    });

    board.innerHTML = html;
    _initDragDrop();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function _derivePlanSections(plan) {
    if (plan && Array.isArray(plan.tagged_sections) && plan.tagged_sections.length) {
        return plan.tagged_sections.map(function(section, index) {
            return {
                id: section.id || ('section-' + index),
                title: section.title || 'Sprint',
                summary: section.summary || '',
                body: section.body || '',
                plan_id: section.plan_id || '',
                sprint_tag: section.sprint_tag || '',
                tasks: Array.isArray(section.tasks) ? section.tasks.slice(0, 8) : [],
                markers: Array.isArray(section.markers) ? section.markers : [],
                direct_markers: Array.isArray(section.direct_markers) ? section.direct_markers : [],
                specs: Array.isArray(section.specs) ? section.specs : []
            };
        });
    }

    var content = plan && plan.content ? String(plan.content) : '';
    if (!content) return [];

    var lines = content.split(/\r?\n/);
    var sections = [];
    var current = null;

    lines.forEach(function(line) {
        var match = line.match(/^##\s+(.+)$/);
        if (match) {
            if (current) sections.push(current);
            current = { id: 'section-' + sections.length, title: match[1].trim(), lines: [], tasks: [] };
            return;
        }
        if (!current) return;
        current.lines.push(line);
        var bullet = line.match(/^\s*(?:[-*]|\d+\.)\s+(?:\[[ xX]\]\s+)?(.+?)\s*$/);
        if (bullet) current.tasks.push(bullet[1].trim());
    });

    if (current) sections.push(current);

    return sections.map(function(section, index) {
        var body = section.lines.join('\n').trim();
        var firstTextLine = body.split('\n').find(function(item) { return item.trim(); }) || '';
        return {
            id: section.id || ('section-' + index),
            title: section.title,
            summary: (section.tasks[0] || firstTextLine).replace(/^#+\s*/, '').trim(),
            body: body,
            tasks: section.tasks.slice(0, 8)
        };
    });
}

function _normalizeCompareText(text) {
    return String(text || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function _findMarkersForPlanSection(section) {
    if (section && section.sprint_tag) {
        return allSections.filter(function(marker) {
            if ((marker.sprint_tag || '') !== section.sprint_tag) return false;
            return true;
        });
    }
    var sectionText = _normalizeCompareText(section.title + ' ' + section.summary);
    var taskTexts = (section.tasks || []).map(_normalizeCompareText);
    return allSections.filter(function(marker) {
        var markerText = _normalizeCompareText((marker.titel || '') + ' ' + (marker.ziel || ''));
        if (!markerText) return false;
        if (taskTexts.some(function(task) { return task && (markerText.indexOf(task) >= 0 || task.indexOf(markerText) >= 0); })) {
            return true;
        }
        return sectionText && (markerText.indexOf(sectionText) >= 0 || sectionText.indexOf(markerText) >= 0);
    });
}

function _sectionSyncState(section, markers) {
    var taskCount = (section.tasks || []).length;
    if (section && Array.isArray(section.specs)) {
        taskCount += section.specs.reduce(function(sum, spec) {
            return sum + ((spec.tasks || []).length || 0);
        }, 0);
    }
    if (!markers.length) return 'empty';
    if (taskCount > 0 && markers.length >= taskCount) return 'synced';
    return 'partial';
}

function _renderSprintSections() {
    var panel = document.getElementById('sprintSectionsPanel');
    var strip = document.getElementById('sprintSectionsStrip');
    var meta = document.getElementById('sprintSectionsMeta');
    if (!panel || !strip) return;

    if (!_planSections.length) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';
    meta.textContent = _planSections.length + ' Sections';
    strip.innerHTML = _planSections.map(function(section) {
        var markers = _findMarkersForPlanSection(section);
        var state = _sectionSyncState(section, markers);
        var selected = _currentPlanSectionId === section.id ? ' is-selected' : '';
        var chips = markers.slice(0, 3).map(function(marker) {
            return '<span class="sprint-section-chip">' + escapeHtml(marker.titel) + '</span>';
        }).join('');
        var specCount = (section.specs || []).length;
        var totalTaskCount = section.tasks.length + (section.specs || []).reduce(function(sum, spec) {
            return sum + ((spec.tasks || []).length || 0);
        }, 0);
        var tasksLabel = totalTaskCount ? (totalTaskCount + ' Tasks') : 'Keine Tasks erkannt';
        var markerLabel = markers.length ? (markers.length + ' Marker') : 'Noch kein Marker';
        return '<button class="sprint-section-card state-' + state + selected + '" type="button" onclick="openPlanSection(\'' + _escapeJsString(section.id) + '\')">'
            + '<div class="sprint-section-top"><span class="sprint-section-state">' + escapeHtml(state === 'synced' ? 'Gemappt' : (state === 'partial' ? 'Teilweise' : 'Offen')) + '</span><span class="sprint-section-map">' + escapeHtml(markerLabel) + '</span></div>'
            + '<div class="sprint-section-name">' + escapeHtml(section.title) + '</div>'
            + '<div class="sprint-section-summary">' + escapeHtml(section.summary || 'Keine Kurzbeschreibung') + '</div>'
            + '<div class="sprint-section-foot"><span>' + escapeHtml(tasksLabel) + '</span><span>' + escapeHtml(specCount + ' Specs') + '</span></div>'
            + '<div class="sprint-section-chips">' + chips + '</div>'
            + '</button>';
    }).join('');
}

function openPlanSection(sectionId) {
    var section = _planSections.find(function(item) { return item.id === sectionId; });
    if (!section) return;

    _currentPlanSectionId = sectionId;
    _renderSprintSections();
    _renderPlanSectionDetails(section);

    document.querySelector('.board-split-view').classList.add('panel-open');
    document.getElementById('panelEmptyState').style.display = 'none';
    document.getElementById('panelContent').style.display = 'flex';
    document.getElementById('panelSectionTitle').textContent = section.title;
    document.getElementById('panelStatusBadge').innerHTML = '<span class="badge ui-badge badge-section-status badge-sec-todo">Source</span>';
    document.getElementById('panelSectionMeta').innerHTML = '<span style="font-weight:600;">Plan Section</span> &middot; ' + escapeHtml((_planInfo && _planInfo.title) || ('Plan ' + PLAN_ID));
    switchPanelTab('source');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

/* === Card bauen === */
function _buildCard(sec) {
    var st = sec.status || 'todo';
    var selected = _currentSection && _currentSection.marker_id === sec.marker_id ? ' selected' : '';
    var locked = sec.is_activatable === false;
    var gateHtml = locked
        ? '<div class="card-gate card-gate--locked"><i data-lucide="lock" class="icon icon-xs"></i> ' + escapeHtml(sec.gate_reason || 'gesperrt') + '</div>'
        : '<div class="card-gate card-gate--ready"><i data-lucide="shield-check" class="icon icon-xs"></i> freigegeben</div>';
    var previewText = sec.ziel || sec.naechster_schritt || '';
    var previewHtml = previewText
        ? '<div class="card-ai-preview"><div class="card-ai-preview-text">' + escapeHtml(previewText) + '</div></div>'
        : '';
    var executionHtml = '';
    if (sec.execution_score !== null && sec.execution_score !== undefined && sec.execution_score !== '') {
        executionHtml = '<div class="card-execution-rating">Execution ' + escapeHtml(String(sec.execution_score)) + '/5'
            + (sec.execution_comment ? ' · ' + escapeHtml(sec.execution_comment) : '')
            + '</div>';
    }

    // Generating indicator
    var genHtml = '';
    if (st === 'in_progress') {
        genHtml = '<div class="card-generating-indicator"><span class="card-generating-dot"></span> Generating...</div>';
    }

    var timeHtml = '';
    if (sec.updated_at) {
        timeHtml = '<span class="card-time">' + (typeof formatTimeAgo === 'function' ? formatTimeAgo(sec.updated_at) : '') + '</span>';
    }

    var activateBtnHtml = sec.is_activatable
        ? '<button class="card-action-btn ui-button ui-button--ghost" onclick="event.stopPropagation();activateMarker(\'' + _escapeJsString(sec.marker_id) + '\')">OK</button>'
        : '';

    return '<div class="plan-card ui-card board-task-card sec-status-' + st + (locked ? ' is-locked' : '') + selected + '" draggable="true" '
        + 'data-marker-id="' + escapeHtml(sec.marker_id) + '" data-status="' + st + '" '
        + 'onclick="openSectionPanel(\'' + _escapeJsString(sec.marker_id) + '\')">'
        + '<div class="card-head">'
        + '<span class="card-kind ui-badge">Marker</span>'
        + '<span class="card-msg-badge ui-badge">' + escapeHtml(st.replace('_', ' ')) + '</span>'
        + '</div>'
        + '<div class="card-title">' + escapeHtml(sec.titel) + '</div>'
        + previewHtml
        + executionHtml
        + genHtml
        + gateHtml
        + '<div class="card-footer">'
        + timeHtml
        + '<div class="card-actions">'
        + activateBtnHtml
        + '<button class="card-action-btn ui-button ui-button--ghost" onclick="event.stopPropagation();openSectionPanel(\'' + _escapeJsString(sec.marker_id) + '\', \'chat\')">Chat</button>'
        + '</div></div></div>';
}

/* === Drag & Drop === */
var _dragSectionId = null;
var _dragSourceStatus = null;

function _initDragDrop() {
    document.querySelectorAll('#sectionsBoard .plan-card[draggable]').forEach(function(card) {
        card.addEventListener('dragstart', function(e) {
            _dragSectionId = this.dataset.markerId;
            _dragSourceStatus = this.dataset.status;
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', _dragSectionId);
        });
        card.addEventListener('dragend', function() {
            this.classList.remove('dragging');
            document.querySelectorAll('.board-column-body.drag-over').forEach(function(el) {
                el.classList.remove('drag-over');
            });
        });
    });

    document.querySelectorAll('#sectionsBoard .board-column-body').forEach(function(colBody) {
        colBody.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.classList.add('drag-over');
        });
        colBody.addEventListener('dragleave', function(e) {
            if (!this.contains(e.relatedTarget)) this.classList.remove('drag-over');
        });
        colBody.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            var targetStatus = this.dataset.status;
            var secId = e.dataTransfer.getData('text/plain');
            if (!secId || targetStatus === _dragSourceStatus) return;
            _moveCard(secId, _dragSourceStatus, targetStatus);
        });
    });
}

function _moveCard(sectionId, oldStatus, newStatus) {
    var card = document.querySelector('.plan-card[data-marker-id="' + sectionId + '"]');
    var targetCol = document.querySelector('.board-column-body[data-status="' + newStatus + '"]');
    if (card && targetCol) {
        var emptyEl = targetCol.querySelector('.column-empty');
        if (emptyEl) emptyEl.remove();
        targetCol.appendChild(card);
        card.dataset.status = newStatus;
        card.classList.remove('sec-status-' + oldStatus);
        card.classList.add('sec-status-' + newStatus);
        _updateColumnCounts();
    }

    api.patch('/api/copilot/markers/' + encodeURIComponent(sectionId) + '/status', {
        project_id: _currentProjectId,
        plan_id: PLAN_ID,
        status: newStatus
    })
        .then(function(data) {
            var col = BOARD_COLUMNS.find(function(c) { return c.status === newStatus; });
            _showToast('Verschoben nach "' + (col ? col.label : newStatus) + '"');
            var sec = allSections.find(function(s) { return s.marker_id === sectionId; });
            if (sec) {
                sec.status = newStatus;
                sec.updated_at = data.updated_at || sec.updated_at;
            }
            _renderProgress();
        })
        .catch(function(err) {
            var sourceCol = document.querySelector('.board-column-body[data-status="' + oldStatus + '"]');
            if (card && sourceCol) {
                sourceCol.appendChild(card);
                card.dataset.status = oldStatus;
                card.classList.remove('sec-status-' + newStatus);
                card.classList.add('sec-status-' + oldStatus);
                _updateColumnCounts();
            }
            _showToast('Fehler: ' + (err.message || 'Update fehlgeschlagen'), true);
        });
}

function _updateColumnCounts() {
    document.querySelectorAll('#sectionsBoard .board-column').forEach(function(col) {
        var el = col.querySelector('.board-count');
        if (el) el.textContent = col.querySelectorAll('.plan-card').length;
    });
}

/* === Add Section === */
function openAddSectionModal() {
    document.getElementById('newSectionTitle').value = '';
    document.getElementById('newSectionKind').value = 'section';
    document.getElementById('newSectionSummary').value = '';
    document.getElementById('newSectionSpecRef').value = '';
    openModal('addSectionModal');
    document.getElementById('newSectionTitle').focus();
}

function createSection() {
    var title = document.getElementById('newSectionTitle').value.trim();
    if (!title) { _showToast('Titel ist erforderlich', true); return; }

    var body = {
        title: title,
        kind: document.getElementById('newSectionKind').value,
        summary: document.getElementById('newSectionSummary').value.trim() || null,
        spec_ref: document.getElementById('newSectionSpecRef').value.trim() || null,
    };

    api.post('/api/plans/' + PLAN_ID + '/sections', body)
        .then(function() {
            closeModal('addSectionModal');
            _showToast('AI Task erstellt');
            _loadSections();
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Erstellen fehlgeschlagen'), true);
        });
}
