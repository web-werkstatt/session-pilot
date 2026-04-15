/**
 * Copilot Board Chat — Panel-Chat, Thread-Mode, Image-Upload, Message-Send.
 * Ausgelagert aus copilot-board-panel.js (Phase 7, 2026-04-14) wegen Dateigroessen-Limit.
 * Nutzt Panel-State aus copilot-board-panel.js: _currentSection, _currentThreadId,
 *   _pendingImages, _currentProjectId, _activePanelTab; Utilities aus
 *   copilot-board-shared.js: _markerThreadId, _projectQueryParam,
 *   _formatTokenCount, _formatUsd, _showToast.
 */

function _loadPanelChat(sectionId) {
    var container = document.getElementById('panelChatMessages');
    container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">...</div>Chat laden...</div>';
    _renderThreadMode(_currentSection, false);

    api.get('/api/copilot/runs?thread_id=' + encodeURIComponent(_markerThreadId(sectionId)) + '&plan_id=' + PLAN_ID + _projectQueryParam())
        .then(function(data) {
            _currentThreadId = _markerThreadId(sectionId);
            var msgs = data.runs || [];
            _renderThreadMode(_currentSection, msgs.length > 0);
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
            _renderThreadMode(_currentSection, false);
            container.innerHTML = '<div class="panel-chat-empty"><div class="panel-chat-empty-icon">⚠️</div>Chat konnte nicht geladen werden.</div>';
        });
}

function _renderThreadMode(marker, hasHistory) {
    var node = document.getElementById('panelThreadMode');
    if (!node) return;
    if (!marker || !marker.marker_id) {
        node.style.display = 'none';
        node.innerHTML = '';
        return;
    }

    // Phase 7 (2026-04-14): Nur echte Chat-History zaehlt.
    // last_session (= Code-Session-Referenz) fuehrte faelschlich dazu, dass
    // "Thread fortsetzen" auch bei done-Markern ohne Chat-Verlauf stand.
    var continuation = hasHistory;
    node.style.display = 'flex';
    node.className = 'panel-thread-mode ' + (continuation ? 'is-continuation' : 'is-fresh');
    node.innerHTML = ''
        + '<div class="panel-thread-mode-title">' + (continuation ? 'Thread fortsetzen' : 'Neuen Thread starten') + '</div>'
        + '<div class="panel-thread-mode-copy">' + escapeHtml(continuation
            ? 'Dieser markergebundene Chat wird im bestehenden Verlauf fortgesetzt.'
            : 'Dieser markergebundene Chat startet als neuer Verlauf fuer diesen Marker.') + '</div>';
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
            a.href = img.url;
            a.target = '_blank';
            a.className = 'chat-img-thumb';
            var thumb = document.createElement('img');
            thumb.src = img.url;
            thumb.alt = img.filename || 'Bild';
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

/* _formatTokenCount, _formatUsd → copilot-board-shared.js */

function _scrollChat() {
    var container = document.getElementById('panelChatMessages');
    container.scrollTop = container.scrollHeight;
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
                if (data.error) {
                    _showToast('Upload-Fehler: ' + data.error, true);
                    return;
                }
                _pendingImages.push({ filename: data.filename, url: data.url, mime_type: data.mime_type });
            })
            .catch(function() { _showToast('Upload fehlgeschlagen', true); });
    });
    input.value = '';
}
