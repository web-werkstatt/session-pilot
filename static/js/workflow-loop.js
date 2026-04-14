(function() {
    var WL = window.WorkflowLoop = window.WorkflowLoop || {};

    function ensureLayout(shell) {
        shell.innerHTML = ''
            + '<div class="workflow-loop-intro">'
            + '<div class="workflow-loop-intro-kicker">Was ist das?</div>'
            + '<h2 class="workflow-loop-intro-title">Operativer Arbeitsfluss fuer Marker</h2>'
            + '<p class="workflow-loop-intro-copy">Der Workflow Loop zeigt, welcher Marker gerade laeuft, was als Naechstes dran ist und wo Ratings oder Risiken offen sind. Hier steuerst du keine Planung, sondern die operative Abarbeitung aus dem Planning heraus.</p>'
            + '<p class="workflow-loop-intro-copy">Typischer Ablauf: naechsten Marker pruefen, Execution starten oder fortsetzen, Ergebnis zurueckschreiben und Abschluss bewerten.</p>'
            + '</div>'
            + '<div class="workflow-loop-grid">'
            + '<div class="workflow-loop-ring" id="workflowLoopRing"></div>'
            + '<div class="workflow-loop-summary" id="workflowLoopSummary"></div>'
            + '<div class="workflow-loop-cards" id="workflowLoopCards"></div>'
            + '<div class="workflow-loop-board" id="workflowLoopBoard"></div>'
            + '</div>';
    }

    async function loadWorkflowLoop(projectName) {
        if (projectName) WL.projectName = projectName;
        var pn = WL.getProjectName();
        var shell = document.getElementById('workflowLoopShell');
        if (!shell || !pn) return;

        shell.classList.remove('is-error');
        shell.classList.remove('is-empty');
        shell.setAttribute('aria-busy', 'true');

        try {
            ensureLayout(shell);
            WL.data = await api.get('/api/project/' + encodeURIComponent(pn) + '/workflow-loop');
            renderWorkflowLoop(shell, WL.data || {});
        } catch (e) {
            shell.classList.add('is-error');
            shell.innerHTML = ''
                + '<div class="workflow-loop-state workflow-loop-state--error">'
                + '<div class="workflow-loop-state-title">Workflow Loop konnte nicht geladen werden</div>'
                + '<button class="workflow-loop-inline-btn" type="button" onclick="loadWorkflowLoop()">Retry</button>'
                + '</div>';
        } finally {
            shell.setAttribute('aria-busy', 'false');
        }
    }

    function renderWorkflowLoop(shell, data) {
        var ring = document.getElementById('workflowLoopRing');
        var summary = document.getElementById('workflowLoopSummary');
        var cards = document.getElementById('workflowLoopCards');
        var board = document.getElementById('workflowLoopBoard');
        var markerGroups = Array.isArray(data.marker_groups) ? data.marker_groups : [];
        var hasMarkers = !!((data.current_marker && data.current_marker.marker_id) || (data.next_marker && data.next_marker.marker_id) || (data.pending_ratings || []).length || markerGroups.some(function(group) {
            return Array.isArray(group.cards) && group.cards.length;
        }));

        if (!hasMarkers) {
            shell.classList.add('is-empty');
        }

        WL.renderSummary(summary, data);
        WL.renderCards(cards, data);
        WL.renderBoard(board, markerGroups);
        renderWorkflowLoopSvg(ring, data, WL.handleStepClick);
    }

    window.loadWorkflowLoop = loadWorkflowLoop;
    window.workflowLoopOpenRating = function(planId, markerId) {
        window.location.href = WL.copilotUrl(planId, markerId, 'history');
    };
})();
