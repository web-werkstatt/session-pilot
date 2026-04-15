/* === Panel === */
function openSectionPanel(sectionId, tab) {
    var sec = allSections.find(function(s) { return s.marker_id === sectionId; });
    if (!sec) {
        // Marker liegt ausserhalb des aktuellen Board-Filters (z.B. anderer Plan).
        // Fallback: zum Projekt-Cockpit wechseln, Deep-Link via Query-Params
        // (wird von copilot_board.js:_openInitialMarkerContext ausgewertet).
        var projectName = (typeof COCKPIT_PROJECT !== 'undefined' && COCKPIT_PROJECT) ? COCKPIT_PROJECT : '';
        if (projectName) {
            var url = '/copilot?project=' + encodeURIComponent(projectName)
                + '&marker_id=' + encodeURIComponent(sectionId);
            if (tab) url += '&tab=' + encodeURIComponent(tab);
            window.location.href = url;
            return;
        }
        if (typeof _showToast === 'function') {
            _showToast('Marker liegt ausserhalb des aktuellen Plan-Filters', true);
        }
        return;
    }

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

    // Modus-Vereinheitlichung: im Projekt-Modus (?project=&marker_id=) den
    // Plan-Header analog zum Plan-Modus rendern, sobald der Marker einen
    // sprint_plan_id hat. So ist der Plan-Kontext bei jedem Deep-Link gleich.
    if (!PLAN_ID && sec.sprint_plan_id && (!_planInfo || _planInfo.id !== sec.sprint_plan_id)) {
        api.get('/api/plans/' + encodeURIComponent(sec.sprint_plan_id))
            .then(function(plan) {
                _planInfo = plan;
                if (typeof _renderPlanContextBanner === 'function') {
                    _renderPlanContextBanner(plan);
                }
                _planSections = (typeof _derivePlanSections === 'function')
                    ? _derivePlanSections(plan)
                    : [];
                _sprintSectionsCollapsed = false;
                if (typeof _renderSprintSections === 'function') _renderSprintSections();
            })
            .catch(function() { /* still no plan-context — UI faellt zurueck */ });
    }

    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function closeSectionPanel() {
    _currentSection = null;
    document.querySelector('.board-split-view').classList.remove('panel-open');
    document.getElementById('panelContent').style.display = 'none';
    document.getElementById('panelEmptyState').style.display = 'flex';
    document.querySelectorAll('#sectionsBoard .plan-card').forEach(function(c) { c.classList.remove('selected'); });
    _updateCockpitBreadcrumb(null);
    if (typeof renderCockpitNextAction === 'function') {
        renderCockpitNextAction(null, null);
    }
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
    _updateCockpitBreadcrumb(tab);
}

/* Breadcrumb-Ergaenzung: bei geoeffnetem Panel Tab-Name anhaengen
   (Workspace / Cockpit / <projekt> / <Tab-Label>). */
var _COCKPIT_TAB_LABELS = {
    chat: 'Chat',
    output: 'Output',
    history: 'Verlauf',
    source: 'Quelle',
    dispatch: 'Dispatch'
};

function _updateCockpitBreadcrumb(tab) {
    var bc = document.querySelector('.breadcrumb');
    if (!bc) return;
    // Vorheriges dynamisches Segment entfernen.
    bc.querySelectorAll('.bc-tab-injected').forEach(function(el) { el.remove(); });
    var label = tab && _COCKPIT_TAB_LABELS[tab];
    if (!label) return;
    var sep = document.createElement('span');
    sep.className = 'bc-sep bc-tab-injected';
    sep.textContent = '/';
    var span = document.createElement('span');
    span.className = 'bc-tab-injected';
    span.textContent = label;
    bc.appendChild(document.createTextNode(' '));
    bc.appendChild(sep);
    bc.appendChild(document.createTextNode(' '));
    bc.appendChild(span);
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
    if (typeof renderCockpitNextAction === 'function') {
        var wf = (typeof _cockpitWorkflowData !== 'undefined' && _cockpitWorkflowData)
            ? _cockpitWorkflowData.workflow : null;
        renderCockpitNextAction(marker, wf);
    }
    _renderImplementationCheck(marker);
}

function _renderImplementationCheck(marker) {
    var box = document.getElementById('panelImplCheck');
    if (!box) return;
    var pct = (typeof marker.implementation_percent === 'number') ? marker.implementation_percent : null;
    var signals = Array.isArray(marker.implementation_signals) ? marker.implementation_signals : [];
    if (pct === null || !signals.length) {
        box.innerHTML = '<div style="font-size:12px;color:var(--cn-text-muted)">Keine Signale verfuegbar.</div>';
        return;
    }
    var items = signals.map(function (s) {
        var done = !!s.done;
        var icon = done ? 'check-circle-2' : 'circle';
        var cls = 'impl-check-icon ' + (done ? 'done' : 'todo');
        return '<div class="impl-check-item' + (done ? ' is-done' : '') + '">'
            + '<span class="' + cls + '"><i data-lucide="' + icon + '" class="icon icon-xs"></i></span>'
            + '<span>' + escapeHtml(s.label || s.key) + '</span>'
            + '<span class="impl-check-weight">' + (s.weight || 0) + '%</span>'
            + '</div>';
    }).join('');
    box.innerHTML = '<div class="impl-check-head">'
        + '<span class="impl-check-title">Automatische Kontrolle</span>'
        + '<span class="impl-check-percent">' + pct + '%</span>'
        + '</div>'
        + '<div class="impl-check-list">' + items + '</div>';
    if (typeof lucide !== 'undefined') lucide.createIcons();
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

    // Drill-Down: Tasks aus DB (per section_key gefiltert) statt rohem Markdown.
    // Fallback auf section.tasks (Strings) wenn kein Plan-Kontext oder DB-Tasks
    // noch nicht persistiert sind (Lazy-Parse erfolgt im /api/plans/<id>-Read).
    var sectionKey = (section.sprint_tag || '').replace(/^#/, '') || (section.id || '').replace(/^sprint:/, '');
    var planIdForTasks = (_planInfo && _planInfo.id) || (PLAN_ID || section.plan_id);
    if (planIdForTasks && sectionKey) {
        api.get('/api/plans/' + encodeURIComponent(planIdForTasks) + '/sections/' + encodeURIComponent(sectionKey) + '/tasks')
            .then(function(data) {
                _renderSectionTasks(section, markers, data && data.tasks ? data.tasks : []);
            })
            .catch(function() {
                _renderSectionTasks(section, markers, []);
            });
    } else {
        _renderSectionTasks(section, markers, []);
    }

    document.getElementById('panelSourceBody').textContent = section.body || '-';
}

/* Drill-Down Section -> Task -> Marker.
 * Rendert Task-Liste mit abgeleitetem Status + Marker-Count, gruppiert
 * zusaetzlich Marker dieser Section nach task_id (Orphan-Bucket "Ohne Task"). */
function _renderSectionTasks(section, sectionMarkers, dbTasks) {
    var tasksHost = document.getElementById('panelSourceTasks');
    var markersHost = document.getElementById('panelSourceMarkers');
    if (!tasksHost || !markersHost) return;

    if (dbTasks && dbTasks.length) {
        tasksHost.innerHTML = dbTasks.map(function(task) {
            var statusCls = 'task-status-' + (task.status || 'open');
            var statusLabel = task.status === 'done' ? 'Done'
                : task.status === 'in_progress' ? 'Active'
                : 'Open';
            var markerInfo = task.marker_count > 0
                ? (task.marker_count + ' Marker')
                : 'Kein Marker';
            return '<button type="button" class="panel-task-item ' + statusCls
                + '" onclick="loadTaskMarkers(' + Number(task.id) + ', this)">'
                + '<span class="panel-task-status-dot"></span>'
                + '<span class="panel-task-title">' + escapeHtml(task.title || '') + '</span>'
                + '<span class="panel-task-meta">' + escapeHtml(statusLabel) + ' · ' + escapeHtml(markerInfo) + '</span>'
                + '</button>';
        }).join('');
    } else {
        // Fallback: Strings aus tagged_sections (vor Lazy-Parse oder ohne Plan-Kontext)
        var allStrings = [].concat(section.tasks || []);
        (section.specs || []).forEach(function(spec) {
            (spec.tasks || []).forEach(function(task) {
                allStrings.push((spec.title ? (spec.title + ': ') : '') + task);
            });
        });
        tasksHost.innerHTML = allStrings.length
            ? allStrings.map(function(t) {
                return '<div class="panel-check-item"><i data-lucide="list-todo" class="icon icon-xs"></i>'
                    + escapeHtml(t) + '</div>';
            }).join('')
            : '<div class="panel-check-empty">Keine Tasks erkannt</div>';
    }

    // Marker-Bucket "Ohne Task" — Section-Marker mit task_id=null bzw. nicht zugeordnet.
    var orphanMarkers = (sectionMarkers || []).filter(function(m) {
        return !m.task_id;
    });
    markersHost.innerHTML = _renderMarkerList(orphanMarkers, 'Ohne Task: keine offenen Marker');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function _renderMarkerList(markers, emptyText) {
    if (!markers || !markers.length) {
        return '<div class="panel-check-empty">' + escapeHtml(emptyText || 'Keine Marker') + '</div>';
    }
    return markers.map(function(marker) {
        var hierarchy = [];
        if (marker.sprint_tag) hierarchy.push(marker.sprint_tag);
        if (marker.spec_tag) hierarchy.push(marker.spec_tag);
        var label = (marker.titel || marker.title || '')
            + (hierarchy.length ? ' · ' + hierarchy.join(' / ') : '');
        var statusBadge = marker.status
            ? ' <span class="panel-marker-status panel-marker-status-' + escapeHtml(marker.status) + '">' + escapeHtml(marker.status) + '</span>'
            : '';
        return '<div class="panel-check-item">'
            + '<i data-lucide="flag" class="icon icon-xs"></i>'
            + escapeHtml(label) + statusBadge
            + '</div>';
    }).join('');
}

/* Klick auf einen Task: laedt zugeordnete Marker und ersetzt den
 * "Zugeordnete Marker"-Bucket mit task-spezifischer Liste. */
function loadTaskMarkers(taskId, btnEl) {
    if (!taskId) return;
    document.querySelectorAll('.panel-task-item').forEach(function(el) {
        el.classList.remove('is-selected');
    });
    if (btnEl) btnEl.classList.add('is-selected');
    var host = document.getElementById('panelSourceMarkers');
    if (host) host.innerHTML = '<div class="panel-check-empty">Lade Marker...</div>';
    api.get('/api/tasks/' + encodeURIComponent(taskId) + '/markers')
        .then(function(data) {
            if (host) host.innerHTML = _renderMarkerList(data && data.markers ? data.markers : [], 'Noch keine Marker fuer diesen Task');
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function() {
            if (host) host.innerHTML = '<div class="panel-check-empty">Fehler beim Laden</div>';
        });
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
