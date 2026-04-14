/**
 * Dispatch — ADR-002 Stufe 2a
 * Projekt-Detail-Tab + Cockpit-Panel-Modus.
 * Nutzt: api.get/post (api.js), escapeHtml (base.js)
 */
var Dispatch = (function() {
    'use strict';
    var _markers = [], _assignments = [], _toolProfiles = [], _roles = [];
    var _loaded = false, _activeFormMarkerId = null;

    function load() {
        if (_loaded) {
            refresh();
            return;
        }
        _loaded = true;
        var el = document.getElementById('dispatchBody');
        if (!el) return;
        el.innerHTML = '<div class="dispatch-loading"><div class="spinner"></div> Loading dispatch data...</div>';
        _loadAll();
    }

    async function _loadAll() {
        try {
            var results = await Promise.all([
                api.get('/api/dispatch/assignments?project=' + encodeURIComponent(PROJECT_NAME)),
                api.get('/api/dispatch/markers?project=' + encodeURIComponent(PROJECT_NAME)),
                api.get('/api/policies/tool-profiles'),
                api.get('/api/policies/roles'),
            ]);
            _assignments = (results[0] && results[0].assignments) || [];
            _markers = (results[1] && results[1].markers) || [];
            _toolProfiles = (results[2] && results[2].tool_profiles) || results[2] || [];
            _roles = (results[3] && results[3].roles) || results[3] || [];
            _render();
        } catch (e) {
            var el = document.getElementById('dispatchBody');
            if (el) el.innerHTML = '<div class="dispatch-empty">Error loading dispatch data: ' + escapeHtml(String(e.message || e)) + '</div>';
        }
    }

    async function refresh() {
        try {
            var results = await Promise.all([
                api.get('/api/dispatch/assignments?project=' + encodeURIComponent(PROJECT_NAME)),
                api.get('/api/dispatch/markers?project=' + encodeURIComponent(PROJECT_NAME)),
            ]);
            _assignments = (results[0] && results[0].assignments) || [];
            _markers = (results[1] && results[1].markers) || [];
            _render();
        } catch (e) { /* silent */ }
    }

    function _filterByState(arr, states) {
        return arr.filter(function(a) { return states.indexOf(a.approval_state) !== -1; });
    }
    var _ACTIVE_STATES = ['proposed', 'approved', 'claimed'];
    var _TERMINAL_STATES = ['completed', 'failed', 'rejected', 'revoked', 'expired'];

    function _render() {
        var el = document.getElementById('dispatchBody');
        if (!el) return;
        var html = '<div class="dispatch-panel">';
        var active = _filterByState(_assignments, _ACTIVE_STATES);
        if (active.length > 0) {
            html += '<div><h3 class="dispatch-section-title">Active Assignments (' + active.length + ')</h3><div class="dispatch-assignment-list">';
            active.forEach(function(a) { html += _renderAssignmentCard(a); });
            html += '</div></div>';
        }
        var open = _markers.filter(function(m) { return m.status !== 'done'; });
        html += '<div><h3 class="dispatch-section-title">Markers</h3>';
        html += '<p class="dispatch-section-subtitle">' + open.length + ' offene Marker — Tool zuweisen per "Assign"</p>';
        if (open.length > 0) {
            html += '<div class="dispatch-marker-list">';
            open.forEach(function(m) { html += _renderMarkerRow(m); });
            html += '</div>';
        }
        html += '<div id="dispatchFormContainer"></div></div>';
        var terminal = _filterByState(_assignments, _TERMINAL_STATES);
        if (terminal.length > 0) {
            html += '<div><h3 class="dispatch-section-title">History (' + terminal.length + ')</h3><div class="dispatch-assignment-list">';
            terminal.slice(0, 20).forEach(function(a) { html += _renderAssignmentCard(a); });
            html += '</div></div>';
        }
        html += '</div>';
        el.innerHTML = html;
        if (_activeFormMarkerId) _showForm(_activeFormMarkerId);
    }

    function _renderMarkerRow(m) {
        var markerAssignment = _assignments.find(function(a) {
            return a.marker_id === m.marker_id &&
                ['proposed', 'approved', 'claimed'].indexOf(a.approval_state) !== -1;
        });

        var html = '<div class="dispatch-marker-row">';
        html += '<span class="dispatch-marker-id">' + escapeHtml(m.marker_id) + '</span>';
        html += '<span class="dispatch-marker-title" title="' + escapeHtml(m.titel || '') + '">' + escapeHtml(m.titel || m.marker_id) + '</span>';
        html += '<span class="dispatch-marker-status dispatch-marker-status--' + escapeHtml(m.status || 'todo') + '">' + escapeHtml(m.status || 'todo') + '</span>';

        if (markerAssignment) {
            html += '<span class="dispatch-marker-assigned">' + escapeHtml(markerAssignment.executor_tool) + ' (' + escapeHtml(markerAssignment.approval_state) + ')</span>';
        } else {
            html += '<button class="dispatch-marker-assign-btn" onclick="Dispatch.openForm(\'' + escapeHtml(m.marker_id) + '\')">Assign</button>';
        }

        html += '</div>';
        return html;
    }

    function _renderAssignmentCard(a) {
        var html = '<div class="dispatch-assignment-card">';

        // Top row
        html += '<div class="dispatch-assignment-top">';
        html += '<span class="dispatch-assignment-id">#' + a.assignment_id + '</span>';
        html += '<span class="dispatch-assignment-tool">' + escapeHtml(a.executor_tool || '?') + '</span>';
        if (a.marker_id) {
            html += '<span class="dispatch-assignment-marker">' + escapeHtml(a.marker_id) + '</span>';
        }
        html += '<span class="dispatch-state dispatch-state--' + escapeHtml(a.approval_state) + '">' + escapeHtml(a.approval_state) + '</span>';
        html += '<span class="dispatch-risk dispatch-risk--' + escapeHtml(a.risk_level || 'medium') + '">' + escapeHtml(a.risk_level || 'medium') + '</span>';
        html += '</div>';

        // Body: meta + review + actions
        html += '<div class="dispatch-assignment-body">';

        // Meta
        html += '<div class="dispatch-assignment-meta">';
        if (a.dispatch_mode) html += '<span>Mode: ' + escapeHtml(a.dispatch_mode) + '</span>';
        if (a.created_by) html += '<span>By: ' + escapeHtml(a.created_by) + '</span>';
        if (a.created_at) html += '<span>' + _formatTime(a.created_at) + '</span>';
        if (a.claimed_by) html += '<span>Claimed: ' + escapeHtml(a.claimed_by) + '</span>';
        html += '</div>';

        // Perplexity Review
        if (a.perplexity_review) {
            html += _renderReview(a.perplexity_review);
        }

        // Actions
        html += '<div class="dispatch-assignment-actions">';
        if (a.approval_state === 'proposed') {
            if (!a.perplexity_review) {
                html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.review(' + a.assignment_id + ')">Perplexity Review</button>';
            }
            html += '<button class="dispatch-btn dispatch-btn--approve" onclick="Dispatch.approve(' + a.assignment_id + ')">Approve</button>';
            html += '<button class="dispatch-btn dispatch-btn--reject" onclick="Dispatch.reject(' + a.assignment_id + ')">Reject</button>';
        }
        if (a.approval_state === 'approved') {
            html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.claim(' + a.assignment_id + ')">Claim (Manual)</button>';
            html += '<button class="dispatch-btn dispatch-btn--ghost" onclick="Dispatch.revoke(' + a.assignment_id + ')">Revoke</button>';
        }
        if (a.approval_state === 'claimed') {
            html += '<button class="dispatch-btn dispatch-btn--approve" onclick="Dispatch.complete(' + a.assignment_id + ')">Complete</button>';
            html += '<button class="dispatch-btn dispatch-btn--reject" onclick="Dispatch.fail(' + a.assignment_id + ')">Fail</button>';
        }
        html += '</div>';

        html += '</div>';
        html += '</div>';
        return html;
    }

    function _renderReview(review) {
        if (!review || review.error) {
            return '<div class="dispatch-review-box"><div class="dispatch-review-header">Perplexity Review — Error</div><div class="dispatch-review-row">' + escapeHtml(String((review && review.error) || 'error')) + '</div></div>';
        }
        var html = '<div class="dispatch-review-box"><div class="dispatch-review-header">Perplexity Review</div>';
        if (review.risk_assessment) html += '<div class="dispatch-review-row"><span class="dispatch-review-label">Risk:</span> ' + escapeHtml(String(review.risk_assessment)) + '</div>';
        if (review.tool_fit_score !== undefined) {
            var fc = review.tool_fit_score >= 70 ? '#22c55e' : review.tool_fit_score >= 40 ? '#f59e0b' : '#ef4444';
            html += '<div class="dispatch-review-row"><span class="dispatch-review-label">Tool Fit:</span> <span style="color:' + fc + ';font-weight:600">' + review.tool_fit_score + '/100</span></div>';
        }
        if (review.recommendation) html += '<div class="dispatch-review-row"><span class="dispatch-review-label">Rec:</span> <span class="dispatch-review-recommendation dispatch-review-recommendation--' + review.recommendation + '">' + escapeHtml(review.recommendation) + '</span></div>';
        if (review.reasoning) html += '<div class="dispatch-review-row" style="font-size:11px;color:rgba(148,163,184,0.6)">' + escapeHtml(String(review.reasoning)) + '</div>';
        return html + '</div>';
    }

    // ── Formular ──
    function openForm(markerId) {
        _activeFormMarkerId = markerId;
        _showForm(markerId);
    }

    function _showForm(markerId) {
        var container = document.getElementById('dispatchFormContainer');
        if (!container) return;

        var marker = _markers.find(function(m) { return m.marker_id === markerId; });
        var markerLabel = marker ? escapeHtml(marker.titel || marker.marker_id) : escapeHtml(markerId);

        var html = '<div class="dispatch-form-overlay active">';
        html += '<div class="dispatch-form-header">';
        html += '<span class="dispatch-form-title">Assign: ' + markerLabel + '</span>';
        html += '<button class="dispatch-form-close" onclick="Dispatch.closeForm()">&times;</button>';
        html += '</div>';

        html += '<div class="dispatch-form-grid">';

        // Tool
        html += '<div class="dispatch-form-group">';
        html += '<label>Tool</label>';
        html += '<select id="dispatchFormTool">';
        html += '<option value="">-- Select Tool --</option>';
        var activeProfiles = (_toolProfiles || []).filter(function(p) { return p.active !== false; });
        activeProfiles.forEach(function(p) {
            html += '<option value="' + escapeHtml(p.tool_id) + '">' + escapeHtml(p.tool_id + (p.tool_name ? ' — ' + p.tool_name : '')) + '</option>';
        });
        html += '</select></div>';

        // Role
        html += '<div class="dispatch-form-group">';
        html += '<label>Role</label>';
        html += '<select id="dispatchFormRole">';
        html += '<option value="">-- Optional --</option>';
        (_roles || []).forEach(function(r) {
            html += '<option value="' + escapeHtml(r.role_id) + '">' + escapeHtml(r.role_id + (r.role_name ? ' — ' + r.role_name : '')) + '</option>';
        });
        html += '</select></div>';

        // Risk
        html += '<div class="dispatch-form-group">';
        html += '<label>Risk Level</label>';
        html += '<select id="dispatchFormRisk">';
        html += '<option value="low">Low</option>';
        html += '<option value="medium" selected>Medium</option>';
        html += '<option value="high">High</option>';
        html += '</select></div>';

        // Dispatch Mode
        html += '<div class="dispatch-form-group">';
        html += '<label>Dispatch Mode</label>';
        html += '<select id="dispatchFormMode">';
        html += '<option value="manual" selected>Manual (A)</option>';
        html += '<option value="pull">Pull (B)</option>';
        html += '</select></div>';

        // Scope (full width)
        html += '<div class="dispatch-form-group dispatch-form-grid--full">';
        html += '<label>Scope (files, code regions)</label>';
        html += '<textarea id="dispatchFormScope" placeholder="z.B. services/dispatch_service.py, routes/dispatch_routes.py"></textarea>';
        html += '</div>';

        html += '</div>'; // grid end

        // Actions
        html += '<div class="dispatch-form-actions">';
        html += '<button class="dispatch-btn dispatch-btn--ghost" onclick="Dispatch.closeForm()">Cancel</button>';
        html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.createAssignment(\'' + escapeHtml(markerId) + '\')">Create Assignment</button>';
        html += '</div>';

        html += '</div>';
        container.innerHTML = html;
    }

    function closeForm() {
        _activeFormMarkerId = null;
        var container = document.getElementById('dispatchFormContainer');
        if (container) container.innerHTML = '';
    }

    // ── API-Aktionen ──
    async function createAssignment(markerId) {
        var tool = document.getElementById('dispatchFormTool');
        if (!tool || !tool.value) {
            alert('Bitte ein Tool auswaehlen.');
            return;
        }

        var roleEl = document.getElementById('dispatchFormRole');
        var riskEl = document.getElementById('dispatchFormRisk');
        var modeEl = document.getElementById('dispatchFormMode');
        var scopeEl = document.getElementById('dispatchFormScope');

        var scopeRef = {};
        if (scopeEl && scopeEl.value.trim()) {
            scopeRef.files = scopeEl.value.trim().split(',').map(function(s) { return s.trim(); });
        }

        try {
            await api.post('/api/dispatch/assignments', {
                project_name: PROJECT_NAME,
                marker_id: markerId,
                executor_tool: tool.value,
                role_id: roleEl ? roleEl.value || null : null,
                risk_level: riskEl ? riskEl.value : 'medium',
                dispatch_mode: modeEl ? modeEl.value : 'manual',
                scope_ref: scopeRef,
            });
            closeForm();
            refresh();
        } catch (e) {
            alert('Fehler: ' + (e.message || e));
        }
    }

    function _refreshAll() { refresh(); _refreshPanel(); }

    async function approve(id) {
        try { await api.post('/api/dispatch/assignments/' + id + '/approve'); _refreshAll(); }
        catch (e) { alert('Fehler: ' + (e.message || e)); }
    }
    async function reject(id) {
        var reason = prompt('Ablehnungsgrund (optional):');
        try { await api.post('/api/dispatch/assignments/' + id + '/reject', { reason: reason || null }); _refreshAll(); }
        catch (e) { alert('Fehler: ' + (e.message || e)); }
    }
    async function revoke(id) {
        var reason = prompt('Widerruf-Grund (optional):');
        try { await api.post('/api/dispatch/assignments/' + id + '/revoke', { reason: reason || null }); _refreshAll(); }
        catch (e) { alert('Fehler: ' + (e.message || e)); }
    }
    async function claim(id) {
        try { await api.post('/api/dispatch/assignments/' + id + '/claim', { claimed_by: 'joseph' }); _refreshAll(); }
        catch (e) { alert('Fehler: ' + (e.message || e)); }
    }
    async function complete(id) {
        try { await api.post('/api/dispatch/assignments/' + id + '/complete', {}); _refreshAll(); }
        catch (e) { alert('Fehler: ' + (e.message || e)); }
    }
    async function fail(id) {
        var reason = prompt('Fehlergrund:');
        try { await api.post('/api/dispatch/assignments/' + id + '/fail', { reason: reason || null }); _refreshAll(); }
        catch (e) { alert('Fehler: ' + (e.message || e)); }
    }
    async function review(id) {
        try { await api.post('/api/dispatch/assignments/' + id + '/review'); _refreshAll(); }
        catch (e) { alert('Review-Fehler: ' + (e.message || e)); }
    }

    // ── Cockpit-Panel ──
    var _panelMarkerId = null, _panelProjectName = null, _panelAssignments = [];

    function loadPanel(markerId, projectName) {
        _panelMarkerId = markerId;
        _panelProjectName = projectName;
        var content = document.getElementById('panelDispatchContent');
        var loading = document.getElementById('panelDispatchLoading');
        if (!content) return;
        if (loading) loading.style.display = 'flex';
        content.innerHTML = '';

        var promises = [
            api.get('/api/dispatch/assignments?project=' + encodeURIComponent(projectName)),
        ];
        if (_toolProfiles.length === 0) {
            promises.push(api.get('/api/policies/tool-profiles'));
            promises.push(api.get('/api/policies/roles'));
        }

        Promise.all(promises).then(function(results) {
            if (loading) loading.style.display = 'none';
            var all = (results[0] && results[0].assignments) || [];
            _panelAssignments = all;
            if (results[1]) _toolProfiles = (results[1] && results[1].tool_profiles) || [];
            if (results[2]) _roles = (results[2] && results[2].roles) || [];
            _renderPanel(content, markerId);
        }).catch(function(e) {
            if (loading) loading.style.display = 'none';
            content.innerHTML = '<div class="dispatch-empty">Fehler: ' + escapeHtml(String(e.message || e)) + '</div>';
        });
    }

    function _refreshPanel() {
        if (_panelMarkerId && _panelProjectName) {
            loadPanel(_panelMarkerId, _panelProjectName);
        }
    }

    function _renderPanel(container, markerId) {
        var markerAssignments = _panelAssignments.filter(function(a) {
            return a.marker_id === markerId;
        });
        var active = markerAssignments.filter(function(a) {
            return ['proposed', 'approved', 'claimed'].indexOf(a.approval_state) !== -1;
        });
        var terminal = markerAssignments.filter(function(a) {
            return ['completed', 'failed', 'rejected', 'revoked', 'expired'].indexOf(a.approval_state) !== -1;
        });

        var html = '';

        if (active.length > 0) {
            html += '<h4 class="dispatch-section-title" style="font-size:13px;margin-top:8px">Active (' + active.length + ')</h4>';
            html += '<div class="dispatch-assignment-list">';
            active.forEach(function(a) { html += _renderAssignmentCard(a); });
            html += '</div>';
        }

        // Assign-Button
        if (active.length === 0) {
            html += '<div style="padding:12px 0">';
            html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.openPanelForm()">Assign Tool to this Marker</button>';
            html += '</div>';
        }

        // Form container
        html += '<div id="dispatchPanelFormContainer"></div>';

        if (terminal.length > 0) {
            html += '<h4 class="dispatch-section-title" style="font-size:13px;margin-top:16px">History (' + terminal.length + ')</h4>';
            html += '<div class="dispatch-assignment-list">';
            terminal.slice(0, 5).forEach(function(a) { html += _renderAssignmentCard(a); });
            html += '</div>';
        }

        if (markerAssignments.length === 0) {
            html += '<div class="dispatch-empty">Kein Assignment. Klicke "Assign" oben.</div>';
        }
        container.innerHTML = html;
    }

    function _showFormInContainer(container) {
        var html = '<div class="dispatch-form-overlay active" style="margin-top:8px">';
        html += '<div class="dispatch-form-header">';
        html += '<span class="dispatch-form-title">Assign Tool</span>';
        html += '<button class="dispatch-form-close" onclick="Dispatch.closePanelForm()">&times;</button>';
        html += '</div>';
        html += '<div class="dispatch-form-grid">';

        html += '<div class="dispatch-form-group">';
        html += '<label>Tool</label><select id="dispatchFormTool"><option value="">-- Select --</option>';
        (_toolProfiles || []).filter(function(p) { return p.active !== false; }).forEach(function(p) {
            html += '<option value="' + escapeHtml(p.tool_id) + '">' + escapeHtml(p.tool_id) + '</option>';
        });
        html += '</select></div>';

        html += '<div class="dispatch-form-group">';
        html += '<label>Risk</label><select id="dispatchFormRisk"><option value="low">Low</option><option value="medium" selected>Medium</option><option value="high">High</option></select></div>';

        html += '</div>';
        html += '<div class="dispatch-form-actions">';
        html += '<button class="dispatch-btn dispatch-btn--ghost" onclick="Dispatch.closePanelForm()">Cancel</button>';
        html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.createPanelAssignment()">Create</button>';
        html += '</div></div>';
        container.innerHTML = html;
    }

    function openPanelForm() {
        var container = document.getElementById('dispatchPanelFormContainer');
        if (!container || !_panelMarkerId) return;
        _showFormInContainer(container);
    }

    function closePanelForm() {
        var container = document.getElementById('dispatchPanelFormContainer');
        if (container) container.innerHTML = '';
    }

    async function createPanelAssignment() {
        var tool = document.getElementById('dispatchFormTool');
        if (!tool || !tool.value) { alert('Bitte Tool auswaehlen.'); return; }
        var riskEl = document.getElementById('dispatchFormRisk');
        try {
            await api.post('/api/dispatch/assignments', {
                project_name: _panelProjectName,
                marker_id: _panelMarkerId,
                executor_tool: tool.value,
                risk_level: riskEl ? riskEl.value : 'medium',
                dispatch_mode: 'manual',
            });
            closePanelForm();
            _refreshPanel();
        } catch (e) {
            alert('Fehler: ' + (e.message || e));
        }
    }

    // ── Helpers ──
    function _formatTime(ts) {
        if (!ts) return '';
        try {
            var d = new Date(ts);
            return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) + ' ' +
                   d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return String(ts).substring(0, 16);
        }
    }

    return {
        load: load,
        refresh: refresh,
        openForm: openForm,
        closeForm: closeForm,
        createAssignment: createAssignment,
        approve: approve,
        reject: reject,
        revoke: revoke,
        claim: claim,
        complete: complete,
        fail: fail,
        review: review,
        loadPanel: loadPanel,
        openPanelForm: openPanelForm,
        closePanelForm: closePanelForm,
        createPanelAssignment: createPanelAssignment,
    };
})();
