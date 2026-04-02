/**
 * Sprint N: Copilot Board UX Redesign — AI-native Work OS
 * Split View: Board links, Panel rechts
 * Rich Cards mit AI-Preview
 */

var BOARD_COLUMNS = [
    { status: 'backlog',      label: 'Backlog',     emoji: '💡', description: 'Noch zu klären' },
    { status: 'ready',        label: 'Ready',       emoji: '🚀', description: 'Bereit für Copilot' },
    { status: 'in_progress',   label: 'In Progress', emoji: '⚡', description: 'Wird bearbeitet' },
    { status: 'review',        label: 'Review',      emoji: '👀', description: 'Zur Kontrolle' },
    { status: 'done',          label: 'Done',        emoji: '✅', description: 'Abgeschlossen' },
    { status: 'blocked',       label: 'Blocked',     emoji: '🚧', description: 'Wartet auf...' },
];

var allSections = [];
var _currentSection = null;
var _currentThreadId = null;
var _pendingImages = [];
var _sectionAiPreviews = {};

document.addEventListener('DOMContentLoaded', function() {
    _loadPlanInfo();
    _loadSections();
    _loadAiPreviews();
});

function _loadPlanInfo() {
    api.get('/api/plans/' + PLAN_ID)
        .then(function(plan) {
            document.getElementById('boardPlanTitle').textContent = plan.title || 'Plan #' + PLAN_ID;
            _updateFlowHint();
        })
        .catch(function() {
            document.getElementById('boardPlanTitle').textContent = 'Plan #' + PLAN_ID;
        });
}

function _loadAiPreviews() {
    api.get('/api/plans/' + PLAN_ID + '/sections')
        .then(function(data) {
            var sections = data.sections || [];
            var sectionIds = sections.map(function(s) { return s.id; });
            if (sectionIds.length === 0) return;
            
            api.get('/api/copilot/ai-previews?section_ids=' + sectionIds.join(','))
                .then(function(previews) {
                    _sectionAiPreviews = previews.previews || {};
                    _renderBoard();
                })
                .catch(function() {});
        })
        .catch(function() {});
}

function _updateFlowHint() {
    var hasBacklog = allSections.some(function(s) { return s.status === 'backlog'; });
    var hasInProgress = allSections.some(function(s) { return s.status === 'in_progress'; });
    var hasReview = allSections.some(function(s) { return s.status === 'review'; });
    var hasDone = allSections.some(function(s) { return s.status === 'done'; });

    document.getElementById('flowStep1').classList.toggle('active', hasBacklog);
    document.getElementById('flowStep2').classList.toggle('active', hasInProgress);
    document.getElementById('flowStep3').classList.toggle('active', hasReview);
    document.getElementById('flowStep4').classList.toggle('active', hasDone);
}

function _loadSections() {
    api.get('/api/plans/' + PLAN_ID + '/sections')
        .then(function(data) {
            allSections = data.sections || [];
            document.getElementById('loading').style.display = 'none';
            document.getElementById('boardSectionCount').textContent = allSections.length + ' Steps';
            if (allSections.length === 0) {
                document.getElementById('sectionsBoard').style.display = 'none';
                document.getElementById('emptyState').style.display = 'block';
            } else {
                document.getElementById('emptyState').style.display = 'none';
                _renderBoard();
            }
            _updateFlowHint();
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function(err) {
            document.getElementById('loading').innerHTML = '<div class="error">Fehler beim Laden</div>';
        });
}

function _renderBoard() {
    var board = document.getElementById('sectionsBoard');
    board.style.display = 'flex';

    var grouped = {};
    BOARD_COLUMNS.forEach(function(col) { grouped[col.status] = []; });
    allSections.forEach(function(sec) {
        var st = sec.status || 'backlog';
        if (grouped[st]) grouped[st].push(sec);
        else grouped['backlog'].push(sec);
    });

    var html = '';
    BOARD_COLUMNS.forEach(function(col) {
        var items = grouped[col.status];
        html += '<div class="board-column" data-status="' + col.status + '">';
        html += '<div class="board-column-header">';
        html += '<span class="column-label"><span class="column-emoji">' + col.emoji + '</span>' + col.label + '</span>';
        html += '<span class="board-count">' + items.length + '</span>';
        html += '</div>';
        html += '<div class="board-description">' + col.description + '</div>';
        html += '<div class="board-column-body" data-status="' + col.status + '">';
        items.forEach(function(sec) {
            html += _buildSectionCard(sec);
        });
        html += '</div></div>';
    });

    board.innerHTML = html;
    _initDragDrop();
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function _buildSectionCard(sec) {
    var st = sec.status || 'backlog';
    var kindLabel = sec.kind === 'spec' ? 'Spec' : 'Step';
    var kindIcon = sec.kind === 'spec' ? 'file-check' : 'zap';
    
    var col = BOARD_COLUMNS.find(function(c) { return c.status === st; });
    var statusBadge = col ? (col.emoji + ' ' + col.label) : st.replace('_', ' ');
    
    var aiPreview = _sectionAiPreviews[sec.id];
    var previewHtml = '';
    if (aiPreview && aiPreview.last_message) {
        var previewText = aiPreview.last_message.substring(0, 60) + (aiPreview.last_message.length > 60 ? '...' : '');
        previewHtml = '<div class="card-ai-preview">'
            + '<div class="card-ai-preview-label"><i data-lucide="sparkles" class="icon"></i> ' + aiPreview.message_count + ' msgs</div>'
            + '<div class="card-ai-preview-text">"' + escapeHtml(previewText) + '"</div>'
            + '</div>';
    } else {
        previewHtml = '<div class="card-meta-row">'
            + '<span class="card-meta-item"><i data-lucide="message-circle" class="icon"></i> 0</span>'
            + '</div>';
    }

    return '<div class="plan-card sec-status-' + st + '" draggable="true" '
        + 'data-section-id="' + sec.id + '" data-status="' + st + '" '
        + 'onclick="openSectionPanel(' + sec.id + ')">'
        + '<div class="card-head">'
        + '<span class="badge badge-cat"><i data-lucide="' + kindIcon + '" class="icon icon-xs"></i> ' + kindLabel + '</span>'
        + '<span class="card-head-title">' + escapeHtml(sec.title) + '</span>'
        + '<span class="badge badge-section-status badge-sec-' + st + '">' + statusBadge + '</span>'
        + '</div>'
        + previewHtml
        + '</div>';
}

function _initDragDrop() {
    document.querySelectorAll('#sectionsBoard .plan-card[draggable]').forEach(function(card) {
        card.addEventListener('dragstart', function(e) {
            _dragSectionId = parseInt(this.dataset.sectionId);
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
            var secId = parseInt(e.dataTransfer.getData('text/plain'));
            if (!secId || targetStatus === _dragSourceStatus) return;
            _moveSectionCard(secId, _dragSourceStatus, targetStatus);
        });
    });
}

var _dragSectionId = null;
var _dragSourceStatus = null;

function _moveSectionCard(sectionId, oldStatus, newStatus) {
    var card = document.querySelector('.plan-card[data-section-id="' + sectionId + '"]');
    var targetCol = document.querySelector('.board-column-body[data-status="' + newStatus + '"]');
    if (card && targetCol) {
        targetCol.appendChild(card);
        card.dataset.status = newStatus;
        
        var badge = card.querySelector('.badge-section-status');
        if (badge) {
            badge.className = 'badge badge-section-status badge-sec-' + newStatus;
            badge.textContent = newStatus.replace('_', ' ');
        }
        
        card.classList.remove('sec-status-' + oldStatus);
        card.classList.add('sec-status-' + newStatus);
        
        var col = BOARD_COLUMNS.find(function(c) { return c.status === newStatus; });
        if (badge && col) {
            badge.textContent = (col.emoji + ' ' + col.label);
        }
        
        _updateColumnCounts();
        _updateFlowHint();
    }

    api.put('/api/plan-sections/' + sectionId, { status: newStatus })
        .then(function() {
            var label = BOARD_COLUMNS.find(function(c) { return c.status === newStatus; });
            _showToast('Verschoben nach "' + (label ? label.label : newStatus) + '"');
            var sec = allSections.find(function(s) { return s.id === sectionId; });
            if (sec) sec.status = newStatus;
        })
        .catch(function(err) {
            var sourceCol = document.querySelector('.board-column-body[data-status="' + oldStatus + '"]');
            if (card && sourceCol) {
                sourceCol.appendChild(card);
                card.dataset.status = oldStatus;
                card.classList.remove('sec-status-' + newStatus);
                card.classList.add('sec-status-' + oldStatus);
                var badge = card.querySelector('.badge-section-status');
                if (badge) {
                    badge.className = 'badge badge-section-status badge-sec-' + oldStatus;
                    var col = BOARD_COLUMNS.find(function(c) { return c.status === oldStatus; });
                    badge.textContent = col ? (col.emoji + ' ' + col.label) : oldStatus.replace('_', ' ');
                }
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
            _showToast('Step erstellt');
            _loadSections();
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Erstellen fehlgeschlagen'), true);
        });
}

function openSectionPanel(sectionId) {
    var sec = allSections.find(function(s) { return s.id === sectionId; });
    if (!sec) return;

    _currentSection = sec;
    _currentThreadId = null;
    _pendingImages = [];

    document.getElementById('panelSectionTitle').textContent = sec.title;
    
    var secStatus = sec.status || 'backlog';
    var col = BOARD_COLUMNS.find(function(c) { return c.status === secStatus; });
    var statusHtml = '<span class="badge badge-section-status badge-sec-' + secStatus + '">' 
        + (col ? col.emoji + ' ' : '') + (col ? col.label : secStatus.replace('_', ' ')) + '</span>';
    
    var metaHtml = statusHtml;
    if (sec.kind === 'spec') {
        metaHtml += ' <span class="badge badge-cat"><i data-lucide="file-check" class="icon icon-xs"></i> Spec</span>';
    }
    if (sec.spec_ref) {
        metaHtml += ' <code class="filename" style="font-size:10px;">' + escapeHtml(sec.spec_ref) + '</code>';
    }
    if (sec.summary) {
        metaHtml += ' <span style="font-size:11px;color:var(--text-secondary);margin-left:8px;">' + escapeHtml(sec.summary) + '</span>';
    }
    document.getElementById('panelSectionMeta').innerHTML = metaHtml;

    var aiPreview = _sectionAiPreviews[sec.id];
    if (aiPreview && aiPreview.last_message) {
        var previewText = aiPreview.last_message.substring(0, 150) + (aiPreview.last_message.length > 150 ? '...' : '');
        document.getElementById('panelAiPreviewText').textContent = previewText;
        document.getElementById('panelAiPreview').style.display = 'block';
    } else {
        document.getElementById('panelAiPreview').style.display = 'none';
    }

    document.getElementById('sectionPanel').classList.add('open');
    _loadPanelChat(sectionId);
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeSectionPanel() {
    document.getElementById('sectionPanel').classList.remove('open');
    _currentSection = null;
}

function _loadPanelChat(sectionId) {
    var container = document.getElementById('panelChatMessages');
    container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">💬</div>Chat laden...</div>';

    api.get('/api/copilot/threads?section_id=' + sectionId + '&plan_id=' + PLAN_ID)
        .then(function(data) {
            _currentThreadId = data.thread_id;
            return api.get('/api/copilot/messages?thread_id=' + data.thread_id + '&limit=50');
        })
        .then(function(data) {
            var msgs = data.messages || [];
            container.innerHTML = '';
            if (msgs.length === 0) {
                container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">💬</div>Noch keine Nachrichten.<br>Stelle eine Frage!</div>';
                return;
            }
            msgs.forEach(function(msg) {
                _appendPanelChatMsg(msg.role, msg.content, msg.images);
            });
            _scrollPanelChat();
        })
        .catch(function() {
            container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">⚠️</div>Chat konnte nicht geladen werden.</div>';
        });
}

function _appendPanelChatMsg(role, text, images) {
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
    container.appendChild(div);
    _scrollPanelChat();
}

function _scrollPanelChat() {
    var c = document.getElementById('panelChatMessages');
    c.scrollTop = c.scrollHeight;
}

function sendPanelMessage() {
    var input = document.getElementById('panelChatInput');
    var message = input.value.trim();
    if (!message && _pendingImages.length === 0) return;
    if (!_currentSection) return;

    var btn = document.getElementById('btnPanelSend');
    btn.disabled = true; btn.textContent = '...';

    _appendPanelChatMsg('user', message || '(Bild)', _pendingImages.length > 0 ? _pendingImages : null);
    input.value = '';

    var body = {
        message: message || '(Bild angehängt)',
        plan_id: PLAN_ID,
        section_id: _currentSection.id,
    };
    if (_currentThreadId) body.thread_id = _currentThreadId;
    if (_pendingImages.length > 0) body.images = _pendingImages;
    _pendingImages = [];

    api.post('/api/copilot/section-chat', body)
        .then(function(data) {
            if (data.thread_id) _currentThreadId = data.thread_id;
            if (data.status === 'success' && data.assistant_message) {
                _appendPanelChatMsg('assistant', data.assistant_message.content);
                _loadAiPreviews();
            } else if (data.error) {
                _appendPanelChatMsg('assistant', 'Fehler: ' + data.error);
            }
        })
        .catch(function(err) {
            var msg = 'Fehler';
            if (err.body && err.body.error) msg = err.body.error;
            else if (err.message) msg = err.message;
            _appendPanelChatMsg('assistant', msg);
        })
        .finally(function() {
            btn.disabled = false; btn.textContent = 'Senden';
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
