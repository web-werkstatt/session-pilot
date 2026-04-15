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
    // Phase 7 (2026-04-14): Plan-Titel aus _cockpitPlans nachschlagen (Cockpit-Modus),
    // damit "Plan 142: Auto-Coder Quality Pipeline" statt nur "Plan 142" steht.
    var planLabel = sec.plan_title || (_planInfo && _planInfo.title) || '';
    if (!planLabel && sec.plan_id && typeof _cockpitPlans !== 'undefined' && _cockpitPlans) {
        var matched = _cockpitPlans.find(function(p) { return String(p.id) === String(sec.plan_id); });
        if (matched && matched.title) planLabel = 'Plan ' + sec.plan_id + ': ' + matched.title;
    }
    if (!planLabel) planLabel = 'Plan ' + (sec.plan_id || String(PLAN_ID));
    metaHtml += ' &middot; ' + escapeHtml(planLabel);
    metaHtml += ' &middot; ' + escapeHtml(sec.is_activatable ? 'freigegeben' : (sec.gate_reason || 'gesperrt'));
    // Workflow-Status Badge im Panel-Header
    var wfLabel = typeof _getWorkflowLabelForMarker === 'function' ? _getWorkflowLabelForMarker(sec.marker_id) : '';
    if (wfLabel) {
        var wfStatus = _getWorkflowStatusForMarker(sec.marker_id);
        var wfTone = (typeof WORKFLOW_STATUS_TONES !== 'undefined' && WORKFLOW_STATUS_TONES[wfStatus]) || 'neutral';
        metaHtml += ' &middot; <span class="card-badge card-badge--wf card-badge--' + wfTone + '">' + escapeHtml(wfLabel) + '</span>';
    }
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
    if (tab === 'dispatch' && typeof Dispatch !== 'undefined') {
        if (_currentSection && _currentSection.marker_id) {
            Dispatch.loadPanel(_currentSection.marker_id, _currentProjectId);
        } else {
            var dc = document.getElementById('panelDispatchContent');
            if (dc) dc.innerHTML = '<div class="dispatch-empty">Waehle einen AI Task (Marker) um Dispatch zu nutzen.</div>';
        }
    }
}

function askCopilot() {
    if (_currentSection) {
        switchPanelTab('chat');
        document.getElementById('panelChatInput').focus();
    } else {
        _showToast('Waehle zuerst einen AI Task aus', true);
    }
}

/* Chat-Funktionen (_loadPanelChat, _renderThreadMode, _appendChatMsg,
 * _buildChatUsageHtml, _scrollChat, sendPanelMessage, handlePanelImageSelect)
 * ausgelagert in copilot-board-chat.js (Phase 7, 2026-04-14). */

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
    document.getElementById('panelMarkerExecutionSummary').textContent = marker.execution_score === null ? (marker.status === 'done' ? 'Abschluss unvollstaendig' : '-') : (String(marker.execution_score) + '/5' + (marker.last_execution_at ? ' · ' + marker.last_execution_at : ''));
    document.getElementById('panelMarkerExecutionComment').textContent = marker.execution_comment || '-';
    document.getElementById('panelExecutionScore').value = marker.execution_score === null ? '' : String(marker.execution_score);
    document.getElementById('panelExecutionCommentInput').value = marker.execution_comment || '';
    document.getElementById('panelMarkerChecks').innerHTML = _renderChecksHtml(marker.checks);
    adoptBtn.style.display = marker.prompt_suggestion ? 'inline-flex' : 'none';
    // Phase 7 (2026-04-14): Initial ohne last_session-Fallback — echte History
    // wird asynchron von _loadPanelChat nachgezogen und aktualisiert den Mode.
    _renderThreadMode(marker, false);
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
