/**
 * Copilot Board — Card-Rendering + Drag & Drop
 * Extrahiert aus copilot_board.js (Commit 5: Unified Cockpit Phase 5)
 *
 * Abhaengigkeiten: copilot-board-shared.js (escapeHtml, _escapeJsString, _normalizeMarker)
 * Globale Variablen: allSections, BOARD_COLUMNS, _currentSection, _currentProjectId, PLAN_ID
 */

/* Workflow + Assignment State (befuellt von _loadSections) */
var _workflowStates = {};
var _activeAssignments = {};
var _cockpitPlans = [];

var WORKFLOW_STATUS_LABELS = {
    planned: 'Geplant',
    ready: 'Bereit',
    active: 'Aktiv',
    write_back: 'Write Back',
    rating: 'Rating offen',
    done: 'Erledigt',
    blocked: 'Blockiert'
};

var WORKFLOW_STATUS_TONES = {
    planned: 'neutral',
    ready: 'info',
    active: 'success',
    write_back: 'warning',
    rating: 'warning',
    done: 'success',
    blocked: 'danger'
};

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
    if (st === 'done' && (sec.execution_score === null || sec.execution_score === undefined || sec.execution_score === '')) {
        executionHtml = '<div class="card-execution-rating">Abschluss unvollstaendig · Rating nachholen</div>';
    } else if (sec.execution_score !== null && sec.execution_score !== undefined && sec.execution_score !== '') {
        executionHtml = '<div class="card-execution-rating">Execution ' + escapeHtml(String(sec.execution_score)) + '/5'
            + (sec.execution_comment ? ' · ' + escapeHtml(sec.execution_comment) : '')
            + '</div>';
    }

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
    var chatButtonLabel = sec.last_session ? 'Thread fortsetzen' : 'Neuen Thread starten';
    if (st === 'done' && (sec.execution_score === null || sec.execution_score === undefined || sec.execution_score === '')) {
        chatButtonLabel = 'Rating nachholen';
    }
    var chatTab = chatButtonLabel === 'Rating nachholen' ? 'history' : 'chat';

    // Badges: Workflow-Status, Plan-Herkunft, Assignment
    var badgesHtml = _buildCardBadges(sec);

    // Implementierungs-Fortschritt (Phase 8, 2026-04-15)
    var implHtml = '';
    if (typeof sec.implementation_percent === 'number') {
        var pct = Math.max(0, Math.min(100, sec.implementation_percent));
        var tone = pct >= 80 ? 'impl-high' : (pct >= 40 ? 'impl-mid' : 'impl-low');
        implHtml = '<div class="card-impl ' + tone + '" title="Implementierungs-Fortschritt: ' + pct + '% (siehe Panel fuer Details)">'
            + '<div class="card-impl-bar"><div class="card-impl-fill" style="width:' + pct + '%"></div></div>'
            + '<span class="card-impl-pct">' + pct + '%</span>'
            + '</div>';
    }

    return '<div class="plan-card ui-card board-task-card sec-status-' + st + (locked ? ' is-locked' : '') + selected + '" draggable="true" '
        + 'data-marker-id="' + escapeHtml(sec.marker_id) + '" data-status="' + st + '" '
        + 'onclick="openSectionPanel(\'' + _escapeJsString(sec.marker_id) + '\')">'
        + '<div class="card-head">'
        + '<span class="card-kind ui-badge">Marker</span>'
        + '<span class="card-msg-badge ui-badge">' + escapeHtml(st.replace('_', ' ')) + '</span>'
        + badgesHtml
        + '</div>'
        + '<div class="card-title">' + escapeHtml(sec.titel) + '</div>'
        + implHtml
        + previewHtml
        + executionHtml
        + genHtml
        + gateHtml
        + '<div class="card-footer">'
        + timeHtml
        + '<div class="card-actions">'
        + activateBtnHtml
        + '<button class="card-action-btn ui-button ui-button--ghost" onclick="event.stopPropagation();openSectionPanel(\'' + _escapeJsString(sec.marker_id) + '\', \'' + chatTab + '\')">' + chatButtonLabel + '</button>'
        + '</div></div></div>';
}

function _buildCardBadges(sec) {
    var parts = [];

    // 1) Workflow-Status Badge
    var wfState = _workflowStates[sec.marker_id];
    var wfStatus = wfState ? String(wfState.workflow_status || '').trim() : '';
    if (wfStatus && wfStatus !== 'planned') {
        var tone = WORKFLOW_STATUS_TONES[wfStatus] || 'neutral';
        var label = WORKFLOW_STATUS_LABELS[wfStatus] || wfStatus;
        parts.push('<span class="card-badge card-badge--wf card-badge--' + tone + '">' + escapeHtml(label) + '</span>');
    }

    // 2) Plan-Herkunft: NICHT mehr auf der Card (Platz fuer Title/Status).
    // Phase 7 (2026-04-14): Plan-Info wird nur noch im rechten Panel angezeigt
    // (openSectionPanel -> panelSectionMeta mit aufgeloestem Plan-Titel).

    // 3) Assignment Badge
    var assignment = _activeAssignments[sec.marker_id];
    if (assignment) {
        var executor = assignment.executor_tool || 'Zugewiesen';
        parts.push('<span class="card-badge card-badge--assign"><i data-lucide="user-check" class="icon icon-xs"></i> ' + escapeHtml(executor) + '</span>');
    }

    return parts.join('');
}

function _getWorkflowStatusForMarker(markerId) {
    var wfState = _workflowStates[markerId];
    if (!wfState) return null;
    var wfStatus = String(wfState.workflow_status || '').trim();
    return wfStatus || null;
}

function _getWorkflowLabelForMarker(markerId) {
    var status = _getWorkflowStatusForMarker(markerId);
    if (!status) return '';
    return WORKFLOW_STATUS_LABELS[status] || status;
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
