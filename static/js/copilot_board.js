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
            var label = plan.title || 'Plan #' + PLAN_ID;
            document.getElementById('planSwitcherLabel').textContent = 'Plan switch';
            document.getElementById('currentPlanTitle').textContent = label;
            if (window.history && window.history.replaceState) {
                window.history.replaceState(null, '', _buildCopilotUrl(PLAN_ID, label));
            }
        })
        .catch(function() {
            _currentMarkerPlanId = String(PLAN_ID);
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
            allSections = (data.markers || []).map(_normalizeMarker);
            document.getElementById('loading').style.display = 'none';
            if (allSections.length === 0) {
                document.getElementById('sectionsBoard').style.display = 'none';
                document.getElementById('emptyState').style.display = 'block';
            } else {
                document.getElementById('emptyState').style.display = 'none';
                _renderBoard();
            }
            _renderProgress();
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function() {
            document.getElementById('loading').innerHTML = '<div class="error">Fehler beim Laden</div>';
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

/* === Panel === */
function openSectionPanel(sectionId, tab) {
    var sec = allSections.find(function(s) { return s.marker_id === sectionId; });
    if (!sec) return;

    _currentSection = sec;
    _currentThreadId = _markerThreadId(sec.marker_id);
    _pendingImages = [];

    // Highlight selected card
    document.querySelectorAll('#sectionsBoard .plan-card').forEach(function(c) { c.classList.remove('selected'); });
    var card = document.querySelector('.plan-card[data-marker-id="' + sectionId + '"]');
    if (card) card.classList.add('selected');

    // Show panel
    document.querySelector('.board-split-view').classList.add('panel-open');
    document.getElementById('panelEmptyState').style.display = 'none';
    document.getElementById('panelContent').style.display = 'flex';

    // Title + Status
    document.getElementById('panelSectionTitle').textContent = sec.titel;
    var st = sec.status || 'todo';
    var col = BOARD_COLUMNS.find(function(c) { return c.status === st; });
    document.getElementById('panelStatusBadge').innerHTML =
        '<span class="badge ui-badge badge-section-status badge-sec-' + st + '">' + (col ? col.label : st) + '</span>';

    // Meta
    var metaHtml = '<span style="font-weight:600;">Marker</span>';
    var planLabel = sec.plan_title || (_planInfo && _planInfo.title) || ('Plan ' + (sec.plan_id || String(PLAN_ID)));
    metaHtml += ' &middot; ' + escapeHtml(planLabel);
    metaHtml += ' &middot; ' + escapeHtml(sec.is_activatable ? 'freigegeben' : (sec.gate_reason || 'gesperrt'));
    document.getElementById('panelSectionMeta').innerHTML = metaHtml;

    // Restore last active tab, or force chat when requested explicitly.
    switchPanelTab(tab || _activePanelTab || 'chat');
    _renderPanelMarkerDetails(sec);
    _loadMarkerContext(sectionId);
    _loadPanelChat(sectionId);
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeSectionPanel() {
    _currentSection = null;
    document.querySelector('.board-split-view').classList.remove('panel-open');
    document.getElementById('panelContent').style.display = 'none';
    document.getElementById('panelEmptyState').style.display = 'flex';
    document.querySelectorAll('#sectionsBoard .plan-card').forEach(function(c) { c.classList.remove('selected'); });
}

/* === Panel Tabs === */
function switchPanelTab(tab) {
    _activePanelTab = tab;
    document.querySelectorAll('.panel-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.querySelectorAll('.panel-tab-body').forEach(function(b) {
        b.classList.toggle('active', b.id === 'tab' + tab.charAt(0).toUpperCase() + tab.slice(1));
    });
}

/* === Ask Copilot === */
function askCopilot() {
    if (_currentSection) {
        switchPanelTab('chat');
        document.getElementById('panelChatInput').focus();
    } else {
        _showToast('Waehle zuerst einen AI Task aus', true);
    }
}

/* === Chat === */
function _loadPanelChat(sectionId) {
    var container = document.getElementById('panelChatMessages');
    container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">...</div>Chat laden...</div>';

    api.get('/api/copilot/runs?thread_id=' + encodeURIComponent(_markerThreadId(sectionId)) + '&plan_id=' + PLAN_ID + _projectQueryParam())
        .then(function(data) {
            _currentThreadId = _markerThreadId(sectionId);
            var msgs = data.runs || [];
            container.innerHTML = '';
            if (msgs.length === 0) {
                container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">💬</div>Noch keine Nachrichten.<br>Stelle eine Frage!</div>';
                return;
            }
            msgs.forEach(function(msg) {
                if (msg.user_message) _appendChatMsg('user', msg.user_message, msg.images, null);
                if (msg.assistant_reply) {
                    _appendChatMsg('assistant', msg.assistant_reply, null, {
                        model: msg.model,
                        input_tokens: msg.input_tokens,
                        output_tokens: msg.output_tokens,
                        total_tokens: msg.total_tokens,
                        cost_usd: msg.cost_usd,
                    });
                }
            });
            _scrollChat();
        })
        .catch(function() {
            container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">⚠️</div>Chat konnte nicht geladen werden.</div>';
        });
}

function _appendChatMsg(role, text, images, usageMeta) {
    var container = document.getElementById('panelChatMessages');
    var empty = container.querySelector('.panel-chat-empty');
    if (empty) empty.remove();

    var div = document.createElement('div');
    div.className = 'chat-msg chat-msg--' + role;

    var label = document.createElement('div');
    label.className = 'chat-msg-label';
    label.textContent = role === 'user' ? 'Du' : role === 'assistant' ? 'Copilot' : 'System';

    var body = document.createElement('div');
    body.className = 'chat-msg-body';
    if (role === 'assistant' && typeof marked !== 'undefined') {
        body.innerHTML = marked.parse(text, { breaks: true, gfm: true });
    } else {
        body.textContent = text;
    }

    if (images && images.length > 0) {
        var imgDiv = document.createElement('div');
        imgDiv.className = 'chat-msg-images';
        images.forEach(function(img) {
            var a = document.createElement('a');
            a.href = img.url; a.target = '_blank'; a.className = 'chat-img-thumb';
            var thumb = document.createElement('img');
            thumb.src = img.url; thumb.alt = img.filename || 'Bild';
            a.appendChild(thumb);
            imgDiv.appendChild(a);
        });
        body.appendChild(imgDiv);
    }

    div.appendChild(label);
    div.appendChild(body);
    var usageHtml = _buildChatUsageHtml(role, usageMeta);
    if (usageHtml) {
        var usage = document.createElement('div');
        usage.className = 'chat-msg-usage';
        usage.innerHTML = usageHtml;
        div.appendChild(usage);
    }
    container.appendChild(div);
    _scrollChat();
}

function _buildChatUsageHtml(role, usageMeta) {
    if (role !== 'assistant' || !usageMeta) return '';
    var parts = [];
    if (usageMeta.model) parts.push(escapeHtml(usageMeta.model));
    if (usageMeta.total_tokens) parts.push(_formatTokenCount(usageMeta.total_tokens) + ' Tok');
    if (usageMeta.cost_usd !== null && usageMeta.cost_usd !== undefined) parts.push(_formatUsd(usageMeta.cost_usd));
    return parts.length ? parts.join(' · ') : '';
}

function _formatTokenCount(value) {
    var num = Number(value || 0);
    if (!isFinite(num)) return '0';
    return num.toLocaleString('de-DE');
}

function _formatUsd(value) {
    var num = Number(value || 0);
    if (!isFinite(num)) return '$0.00';
    if (num < 0.01) return '$' + num.toFixed(4);
    if (num < 1) return '$' + num.toFixed(2);
    return '$' + num.toFixed(2);
}

function _scrollChat() {
    var c = document.getElementById('panelChatMessages');
    c.scrollTop = c.scrollHeight;
}

function sendPanelMessage() {
    var input = document.getElementById('panelChatInput');
    var message = input.value.trim();
    if (!message && _pendingImages.length === 0) return;
    if (!_currentSection) return;

    var btn = document.getElementById('btnPanelSend');
    btn.disabled = true;

    _appendChatMsg('user', message || '(Bild)', _pendingImages.length > 0 ? _pendingImages : null);
    input.value = '';

    var body = {
        message: message || '(Bild angehaengt)',
        project_id: _currentProjectId,
        plan_id: PLAN_ID,
        thread_id: _currentThreadId || _markerThreadId(_currentSection.marker_id),
        context: {
            marker_id: _currentSection.marker_id,
            titel: _currentSection.titel,
            status: _currentSection.status,
            ziel: _currentSection.ziel,
            naechster_schritt: _currentSection.naechster_schritt,
            prompt: _currentSection.prompt || '',
            checks: _currentSection.checks || [],
            risiko: _currentSection.risiko || ''
        }
    };
    if (_pendingImages.length > 0) body.images = _pendingImages;
    _pendingImages = [];

    api.post('/api/copilot/chat', body)
        .then(function(data) {
            if (data.thread_id) _currentThreadId = data.thread_id;
            if (data.status === 'success' && data.reply) {
                _appendChatMsg('assistant', data.reply, null, {
                    model: data.model,
                    input_tokens: data.input_tokens,
                    output_tokens: data.output_tokens,
                    total_tokens: data.total_tokens,
                    cost_usd: data.cost_usd,
                });
            } else if (data.error) {
                _appendChatMsg('assistant', 'Fehler: ' + data.error, null, null);
            }
        })
        .catch(function(err) {
            var msg = 'Fehler';
            if (err.body && err.body.error) msg = err.body.error;
            else if (err.message) msg = err.message;
            _appendChatMsg('assistant', msg, null, null);
        })
        .finally(function() {
            btn.disabled = false;
            input.focus();
        });
}

function handlePanelImageSelect(input) {
    if (!input.files || input.files.length === 0) return;
    Array.from(input.files).forEach(function(file) {
        var formData = new FormData();
        formData.append('file', file);
        api.request('/api/copilot/upload_image', { method: 'POST', body: formData, raw: true })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) { _showToast('Upload-Fehler: ' + data.error, true); return; }
                _pendingImages.push({ filename: data.filename, url: data.url, mime_type: data.mime_type });
            })
            .catch(function() { _showToast('Upload fehlgeschlagen', true); });
    });
    input.value = '';
}

/* === Helpers === */
function _showToast(msg, isError) {
    var toast = document.getElementById('syncToast');
    if (toast) {
        toast.textContent = msg;
        toast.className = 'toast show' + (isError ? ' toast-error' : '');
        setTimeout(function() { toast.className = 'toast'; }, 4000);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function _escapeJsString(text) {
    return String(text || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function _slugifyPlanTitle(text) {
    return String(text || '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'plan';
}

function _buildCopilotUrl(planId, planTitle) {
    var url = '/copilot?plan_id=' + encodeURIComponent(planId);
    var slug = _slugifyPlanTitle(planTitle);
    if (slug) url += '&plan=' + encodeURIComponent(slug);
    return url;
}

function _buildMarkerApiUrl(markerId) {
    var url = '/api/copilot/markers';
    if (markerId) url += '/' + encodeURIComponent(markerId);
    url += '?plan_id=' + encodeURIComponent(PLAN_ID);
    if (_currentMarkerPlanId && String(_currentMarkerPlanId) !== String(PLAN_ID)) {
        url = '/api/copilot/markers';
        if (markerId) url += '/' + encodeURIComponent(markerId);
        url += '?plan_id=' + encodeURIComponent(_currentMarkerPlanId);
    }
    if (_currentProjectId) url += '&project_id=' + encodeURIComponent(_currentProjectId);
    return url;
}

function _projectQueryParam() {
    return _currentProjectId ? '&project_id=' + encodeURIComponent(_currentProjectId) : '';
}

function _normalizeMarker(marker) {
    var normalized = Object.assign({}, marker || {});
    normalized.marker_id = String(normalized.marker_id || '');
    normalized.status = normalized.status || 'todo';
    normalized.titel = normalized.titel || 'Unbenannter Marker';
    normalized.plan_title = normalized.plan_title || ((_planInfo && _planInfo.title) ? _planInfo.title : '');
    normalized.ziel = normalized.ziel || '';
    normalized.naechster_schritt = normalized.naechster_schritt || '';
    normalized.prompt = normalized.prompt || '';
    normalized.prompt_suggestion = normalized.prompt_suggestion || '';
    normalized.risiko = normalized.risiko || '';
    normalized.checks = Array.isArray(normalized.checks) ? normalized.checks : [];
    normalized.last_session = normalized.last_session || '';
    normalized.updated_at = normalized.updated_at || '';
    normalized.is_activatable = normalized.is_activatable === true;
    normalized.gate_reason = normalized.gate_reason || '';
    return normalized;
}

function _loadMarkerContext(markerId) {
    api.get(_buildMarkerApiUrl(markerId))
        .then(function(marker) {
            var normalized = _normalizeMarker(marker);
            _currentSection = normalized;
            _upsertSection(normalized);
            _renderPanelMarkerDetails(normalized);
            _renderBoard();
            _renderProgress();
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Marker konnte nicht geladen werden'), true);
        });
}

function _renderPanelMarkerDetails(marker) {
    var outputEmpty = document.getElementById('panelOutputEmpty');
    var outputFields = document.getElementById('panelOutputFields');
    var historyEmpty = document.getElementById('panelHistoryEmpty');
    var historyFields = document.getElementById('panelHistoryFields');
    var adoptBtn = document.getElementById('panelAdoptSuggestionBtn');

    outputEmpty.style.display = 'none';
    outputFields.style.display = 'flex';
    historyEmpty.style.display = 'none';
    historyFields.style.display = 'flex';

    document.getElementById('panelMarkerGoal').textContent = marker.ziel || '-';
    document.getElementById('panelMarkerNextStep').textContent = marker.naechster_schritt || '-';
    document.getElementById('panelMarkerPrompt').value = marker.prompt || '';
    document.getElementById('panelMarkerRisk').textContent = marker.risiko || '-';
    document.getElementById('panelMarkerLastSession').textContent = marker.last_session || '-';
    document.getElementById('panelMarkerUpdatedAt').textContent = marker.updated_at || '-';
    document.getElementById('panelMarkerGate').textContent = marker.is_activatable ? 'freigegeben' : (marker.gate_reason || 'gesperrt');
    document.getElementById('panelMarkerChecks').innerHTML = _renderChecksHtml(marker.checks);
    adoptBtn.style.display = marker.prompt_suggestion ? 'inline-flex' : 'none';
}

function _renderChecksHtml(checks) {
    if (!checks || checks.length === 0) {
        return '<div class="panel-check-empty">Keine checks definiert</div>';
    }
    return checks.map(function(item) {
        return '<div class="panel-check-item"><i data-lucide="check" class="icon icon-xs"></i>' + escapeHtml(item) + '</div>';
    }).join('');
}

function _upsertSection(marker) {
    var idx = allSections.findIndex(function(item) { return item.marker_id === marker.marker_id; });
    if (idx >= 0) allSections[idx] = Object.assign({}, allSections[idx], marker);
    else allSections.push(marker);
}

function _markerThreadId(markerId) {
    return 'marker:' + PLAN_ID + ':' + markerId;
}

function activateMarker(markerId) {
    var marker = allSections.find(function(item) { return item.marker_id === markerId; });
    if (!marker) return;
    if (!marker.is_activatable) {
        _showToast(marker.gate_reason || 'Marker ist nicht freigegeben', true);
        return;
    }

    api.post('/api/copilot/markers/' + encodeURIComponent(markerId) + '/activate', {
        project_id: _currentProjectId,
        plan_id: PLAN_ID,
        context_path: 'marker-context.md'
    })
        .then(function(data) {
            marker.status = data.status || 'in_progress';
            marker.updated_at = data.updated_at || marker.updated_at;
            _upsertSection(marker);
            if (_currentSection && _currentSection.marker_id === markerId) {
                _currentSection.status = marker.status;
                _currentSection.updated_at = marker.updated_at;
            }
            _renderBoard();
            _renderProgress();
            if (_currentSection && _currentSection.marker_id === markerId) {
                openSectionPanel(markerId, _activePanelTab || 'chat');
            }
            if (typeof lucide !== 'undefined') lucide.createIcons();
        _showToast('Kontext vorbereitet, du kannst jetzt Claude Code starten.');
        })
        .catch(function(err) {
            var body = err && err.body ? err.body : {};
            if (body.error === 'gate_blocked') {
                _showToast(body.reason || marker.gate_reason || 'Gate blockiert', true);
                return;
            }
            _showToast('Fehler: ' + (body.error || err.message || 'Aktivierung fehlgeschlagen'), true);
        });
}

function importSprintMarkers() {
    var markerPlanId = _currentMarkerPlanId || String(PLAN_ID);
    var sprintPath = _deriveSprintPath();
    if (!sprintPath) {
        _showToast('Sprint-Pfad konnte nicht bestimmt werden', true);
        return;
    }

    return api.post('/api/sprint/' + encodeURIComponent(markerPlanId) + '/to-markers', {
        project_id: _currentProjectId,
        db_plan_id: PLAN_ID,
        sprint_path: sprintPath
    })
        .then(function(data) {
            _showToast(data.count + ' Marker aus Sprint ' + markerPlanId + ' erzeugt/aktualisiert');
            return _loadSections();
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Sprint-Import fehlgeschlagen'), true);
        });
}

function closeMarkerSession(markerId, payload) {
    var body = payload || {};
    if (!body.project_id && _currentProjectId) body.project_id = _currentProjectId;
    if (!body.plan_id) body.plan_id = PLAN_ID;

    return api.post('/api/copilot/markers/' + encodeURIComponent(markerId) + '/close', body)
        .then(function(data) {
            _showToast('Marker-Status aktualisiert');
            _loadSections();
            if (_currentSection && _currentSection.marker_id === markerId) {
                _loadMarkerContext(markerId);
            }
            return data;
        });
}

function _extractMarkerPlanId(plan) {
    var content = plan && plan.content ? String(plan.content) : '';
    var match = content.match(/plan-id:\s*([^\s*]+)/i);
    return match ? match[1].trim() : null;
}

function _deriveSprintPath() {
    if (_planInfo && _planInfo.filename) {
        return 'upload/Sprints/' + _planInfo.filename;
    }
    var markerPlanId = _currentMarkerPlanId || String(PLAN_ID);
    return 'upload/Sprints/' + markerPlanId + '.md';
}

function adoptPromptSuggestion() {
    if (!_currentSection || !_currentSection.prompt_suggestion) return;

    api.patch('/api/copilot/markers/' + encodeURIComponent(_currentSection.marker_id) + '/fields', {
        project_id: _currentProjectId,
        plan_id: PLAN_ID,
        fields: { prompt: _currentSection.prompt_suggestion }
    })
        .then(function(marker) {
            var normalized = _normalizeMarker(marker);
            _currentSection = normalized;
            _upsertSection(normalized);
            _renderPanelMarkerDetails(normalized);
            _renderBoard();
            _renderProgress();
            if (typeof lucide !== 'undefined') lucide.createIcons();
            _showToast('Prompt-Vorschlag uebernommen');
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Vorschlag konnte nicht uebernommen werden'), true);
        });
}
