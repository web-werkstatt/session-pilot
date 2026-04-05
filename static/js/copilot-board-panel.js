/* === Panel === */
function openSectionPanel(sectionId, tab) {
    var sec = allSections.find(function(s) { return s.marker_id === sectionId; });
    if (!sec) return;

    _currentSection = sec;
    _currentThreadId = _markerThreadId(sec.marker_id);
    _pendingImages = [];

    document.querySelectorAll('#sectionsBoard .plan-card').forEach(function(c) { c.classList.remove('selected'); });
    var card = document.querySelector('.plan-card[data-marker-id="' + sectionId + '"]');
    if (card) card.classList.add('selected');

    document.querySelector('.board-split-view').classList.add('panel-open');
    document.getElementById('panelEmptyState').style.display = 'none';
    document.getElementById('panelContent').style.display = 'flex';

    document.getElementById('panelSectionTitle').textContent = sec.titel;
    var st = sec.status || 'todo';
    var col = BOARD_COLUMNS.find(function(c) { return c.status === st; });
    document.getElementById('panelStatusBadge').innerHTML =
        '<span class="badge ui-badge badge-section-status badge-sec-' + st + '">' + (col ? col.label : st) + '</span>';

    var metaHtml = '<span style="font-weight:600;">Marker</span>';
    var planLabel = sec.plan_title || (_planInfo && _planInfo.title) || ('Plan ' + (sec.plan_id || String(PLAN_ID)));
    metaHtml += ' &middot; ' + escapeHtml(planLabel);
    metaHtml += ' &middot; ' + escapeHtml(sec.is_activatable ? 'freigegeben' : (sec.gate_reason || 'gesperrt'));
    document.getElementById('panelSectionMeta').innerHTML = metaHtml;

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

function switchPanelTab(tab) {
    _activePanelTab = tab;
    document.querySelectorAll('.panel-tab').forEach(function(t) {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.querySelectorAll('.panel-tab-body').forEach(function(b) {
        b.classList.toggle('active', b.id === 'tab' + tab.charAt(0).toUpperCase() + tab.slice(1));
    });
}

function askCopilot() {
    if (_currentSection) {
        switchPanelTab('chat');
        document.getElementById('panelChatInput').focus();
    } else {
        _showToast('Waehle zuerst einen AI Task aus', true);
    }
}

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
    document.getElementById('panelMarkerExecutionSummary').textContent = marker.execution_score === null ? '-' : (String(marker.execution_score) + '/5' + (marker.last_execution_at ? ' · ' + marker.last_execution_at : ''));
    document.getElementById('panelMarkerExecutionComment').textContent = marker.execution_comment || '-';
    document.getElementById('panelExecutionScore').value = marker.execution_score === null ? '' : String(marker.execution_score);
    document.getElementById('panelExecutionCommentInput').value = marker.execution_comment || '';
    document.getElementById('panelMarkerChecks').innerHTML = _renderChecksHtml(marker.checks);
    adoptBtn.style.display = marker.prompt_suggestion ? 'inline-flex' : 'none';
    if (_currentPlanSectionId) {
        var section = _planSections.find(function(item) { return item.id === _currentPlanSectionId; });
        if (section) _renderPlanSectionDetails(section);
    }
}

function _renderPlanSectionDetails(section) {
    var empty = document.getElementById('panelSourceEmpty');
    var fields = document.getElementById('panelSourceFields');
    if (!empty || !fields) return;

    if (!section) {
        empty.style.display = 'flex';
        fields.style.display = 'none';
        return;
    }

    var markers = _findMarkersForPlanSection(section);
    empty.style.display = 'none';
    fields.style.display = 'flex';
    document.getElementById('panelSourceSectionTitle').textContent = section.title;
    document.getElementById('panelSourceSectionSummary').textContent = section.summary || section.sprint_tag || '-';
    var allTasks = [].concat(section.tasks || []);
    (section.specs || []).forEach(function(spec) {
        (spec.tasks || []).forEach(function(task) {
            allTasks.push((spec.title ? (spec.title + ': ') : '') + task);
        });
    });
    document.getElementById('panelSourceTasks').innerHTML = allTasks.length ? allTasks.map(function(task) {
        return '<div class="panel-check-item"><i data-lucide="list-todo" class="icon icon-xs"></i>' + escapeHtml(task) + '</div>';
    }).join('') : '<div class="panel-check-empty">Keine Tasks erkannt</div>';
    document.getElementById('panelSourceMarkers').innerHTML = markers.length ? markers.map(function(marker) {
        var hierarchy = [];
        if (marker.sprint_tag) hierarchy.push(marker.sprint_tag);
        if (marker.spec_tag) hierarchy.push(marker.spec_tag);
        return '<div class="panel-check-item"><i data-lucide="flag" class="icon icon-xs"></i>' + escapeHtml(marker.titel + (hierarchy.length ? ' · ' + hierarchy.join(' / ') : '')) + '</div>';
    }).join('') : '<div class="panel-check-empty">Noch keine zugeordneten Marker</div>';
    document.getElementById('panelSourceBody').textContent = section.body || '-';
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
            _renderSprintSections();
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
            _renderSprintSections();
            _renderProgress();
            if (typeof lucide !== 'undefined') lucide.createIcons();
            _showToast('Prompt-Vorschlag uebernommen');
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Vorschlag konnte nicht uebernommen werden'), true);
        });
}

function saveMarkerExecutionRating() {
    if (!_currentSection) return;
    var score = document.getElementById('panelExecutionScore').value;
    var comment = document.getElementById('panelExecutionCommentInput').value.trim();
    if (score === '') {
        _showToast('Score 0-5 waehlen', true);
        return;
    }

    api.post('/api/marker/' + encodeURIComponent(_currentSection.marker_id) + '/execution-rating', {
        project_id: _currentProjectId,
        plan_id: PLAN_ID,
        execution_score: Number(score),
        execution_comment: comment,
        sessionid: _currentSection.last_session || null
    })
        .then(function(rating) {
            _currentSection.execution_score = rating.execution_score;
            _currentSection.execution_comment = rating.execution_comment || '';
            _currentSection.last_execution_at = rating.last_execution_at || '';
            _upsertSection(_currentSection);
            _renderPanelMarkerDetails(_currentSection);
            _renderBoard();
            _renderSprintSections();
            _showToast('Execution Rating gespeichert');
        })
        .catch(function(err) {
            var body = err && err.body ? err.body : {};
            _showToast('Fehler: ' + (body.error || err.message || 'Rating fehlgeschlagen'), true);
        });
}
