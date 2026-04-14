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
var _initialMarkerId = null;
var _initialPanelTab = null;

document.addEventListener('DOMContentLoaded', function() {
    var params = new URLSearchParams(window.location.search);
    _initialMarkerId = params.get('marker_id');
    _initialPanelTab = params.get('tab');
    _loadPlanInfo()
        .finally(function() {
            _loadSections();
            _loadPlanSwitcher();
            if (COCKPIT_PROJECT && typeof loadCockpitWorkflow === 'function') loadCockpitWorkflow();
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
    // Projekt-Modus: kein Plan geladen, Projekt aus COCKPIT_PROJECT
    if (!PLAN_ID && COCKPIT_PROJECT) {
        _currentProjectId = COCKPIT_PROJECT;
        _planSections = [];
        document.getElementById('planSwitcherLabel').textContent = 'Plan switch';
        document.getElementById('currentPlanTitle').textContent = COCKPIT_PROJECT;
        return Promise.resolve();
    }
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

/* _loadPlanSwitcher, togglePlanSwitcher, switchPlan → copilot-board-shared.js */

/* === Sections laden === */
function _loadSections() {
    var url = (!PLAN_ID && COCKPIT_PROJECT)
        ? '/api/cockpit/project/' + encodeURIComponent(COCKPIT_PROJECT)
        : _buildMarkerApiUrl();
    api.get(url)
        .then(function(data) {
            allSections = _filterMarkersForWorkspace((data.markers || []).map(_normalizeMarker));
            // Cockpit-API liefert Workflow-States, Assignments, Plans
            if (data.workflow && data.workflow.workflow_states) {
                _workflowStates = data.workflow.workflow_states;
            }
            if (data.assignments) {
                _activeAssignments = data.assignments;
            }
            if (data.plans) {
                _cockpitPlans = data.plans;
            }
            var parseErrors = Array.isArray(data.parse_errors) ? data.parse_errors : [];
            document.getElementById('loading').style.display = 'none';
            _renderMarkerParseErrors(parseErrors);
            if (allSections.length === 0) {
                document.getElementById('sectionsBoard').style.display = 'none';
                document.getElementById('emptyState').style.display = 'block';
            } else {
                document.getElementById('emptyState').style.display = 'none';
                _renderBoard();
                _openInitialMarkerContext();
            }
            _renderSprintSections();
            _renderProgress();
            if (typeof lucide !== 'undefined') lucide.createIcons();
        })
        .catch(function(err) {
            var msg = (err && err.message) ? err.message : 'Fehler beim Laden';
            document.getElementById('loading').innerHTML = '<div class="error">' + escapeHtml(msg) + '</div>';
        });
}

function _openInitialMarkerContext() {
    if (!_initialMarkerId) return;
    var markerExists = allSections.some(function(item) { return item.marker_id === _initialMarkerId; });
    if (!markerExists) return;
    openSectionPanel(_initialMarkerId, _initialPanelTab || 'chat');
    _initialMarkerId = null;
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

/* _buildCard, _buildCardBadges, Drag&Drop → copilot-board-cards.js */

/* === Add Section === */
/* openAddSectionModal + createSection sind nach copilot-section-modal.js ausgelagert */
