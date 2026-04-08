(function() {
    function ensureWorkflowLoopLayout(shell) {
        shell.innerHTML = ''
            + '<div class="workflow-loop-grid">'
            + '<div class="workflow-loop-ring" id="workflowLoopRing"></div>'
            + '<div class="workflow-loop-summary" id="workflowLoopSummary"></div>'
            + '<div class="workflow-loop-cards" id="workflowLoopCards"></div>'
            + '</div>';
    }

    async function loadWorkflowLoop() {
        var shell = document.getElementById('workflowLoopShell');
        if (!shell) return;

        shell.classList.remove('is-error');
        shell.classList.remove('is-empty');
        shell.setAttribute('aria-busy', 'true');

        try {
            ensureWorkflowLoopLayout(shell);
            var data = await api.get('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/workflow-loop');
            renderWorkflowLoop(shell, data || {});
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
        var hasMarkers = !!((data.current_marker && data.current_marker.marker_id) || (data.next_marker && data.next_marker.marker_id) || (data.pending_ratings || []).length);

        if (!hasMarkers) {
            shell.classList.add('is-empty');
        }

        renderWorkflowSummary(summary, data);
        renderWorkflowCards(cards, data);
        renderWorkflowLoopSvg(ring, data, handleWorkflowStepClick);
    }

    function renderWorkflowSummary(container, data) {
        if (!container) return;
        var currentMarker = data.current_marker || {};
        var nextMarker = data.next_marker || {};
        var headline = currentMarker.title || nextMarker.title || 'Noch keine Marker vorhanden';
        var stepLabel = workflowLoopCurrentStepLabel(data);
        var copy = '';
        var ctaLabel = '';

        if (currentMarker.rating_pending) {
            copy = 'Abschluss unvollstaendig. Das Rating fuer den letzten Abschluss fehlt noch.';
            ctaLabel = 'Rating nachholen';
        } else if (currentMarker.status === 'in_progress') {
            copy = currentMarker.next_step || 'Thread fortsetzen und den Marker sauber abschliessen.';
            ctaLabel = currentMarker.last_session ? 'Thread fortsetzen' : 'Execution oeffnen';
        } else if (nextMarker.marker_id) {
            copy = nextMarker.recommendation_reason || 'Naechsten Marker fuer die Execution vorbereiten.';
            ctaLabel = nextMarker.gate_status === 'blocked' ? 'Marker pruefen' : 'Execution oeffnen';
        } else {
            copy = 'Noch keine Marker vorhanden';
            ctaLabel = 'Planning oeffnen';
        }

        var pills = [];
        if (currentMarker.status) pills.push(workflowLoopStatusLabel(currentMarker));
        if (nextMarker.gate_status === 'blocked') pills.push('Gate blockiert');
        if (currentMarker.plan_title) pills.push(currentMarker.plan_title);
        else if (nextMarker.plan_title) pills.push(nextMarker.plan_title);

        container.innerHTML = ''
            + '<div class="workflow-loop-kicker">Workflow Loop</div>'
            + '<h2 class="workflow-loop-summary-title">' + escapeHtml(headline) + '</h2>'
            + '<div class="workflow-loop-summary-step">' + escapeHtml(stepLabel) + '</div>'
            + '<p class="workflow-loop-summary-copy">' + escapeHtml(copy) + '</p>'
            + '<div class="workflow-loop-summary-pills">' + pills.map(function(item) {
                return '<span class="workflow-loop-pill">' + escapeHtml(item) + '</span>';
            }).join('') + '</div>'
            + '<div class="workflow-loop-summary-actions">'
            + workflowLoopButtonHtml(ctaLabel, data)
            + '</div>';
    }

    function renderWorkflowCards(container, data) {
        if (!container) return;

        var currentMarker = data.current_marker || {};
        var nextMarker = data.next_marker || {};
        var pendingRatings = Array.isArray(data.pending_ratings) ? data.pending_ratings : [];
        var hints = data.signals && Array.isArray(data.signals.priority_hints) ? data.signals.priority_hints : [];

        container.innerHTML = ''
            + workflowCardCurrentMarker(currentMarker)
            + workflowCardNextMarker(nextMarker)
            + workflowCardPendingRatings(pendingRatings)
            + workflowCardPriorityHints(hints, data.signals || {});
    }

    function workflowCardCurrentMarker(currentMarker) {
        if (!currentMarker.marker_id) {
            return workflowEmptyCard('workflowCardCurrentMarker', 'Aktiver Marker', 'Aktuell laeuft kein aktiver Marker.');
        }

        var meta = [];
        if (currentMarker.last_session) meta.push('Session ' + currentMarker.last_session);
        if (currentMarker.execution_score !== null && currentMarker.execution_score !== undefined) meta.push('Execution ' + currentMarker.execution_score + '/5');
        if (currentMarker.gate_status === 'blocked' && currentMarker.gate_reason) meta.push(currentMarker.gate_reason);

        return workflowCardShell(
            'workflowCardCurrentMarker',
            'Aktiver Marker',
            currentMarker.title,
            currentMarker.next_step || workflowLoopStatusLabel(currentMarker),
            meta,
            currentMarker.rating_pending ? 'Rating nachholen' : (currentMarker.last_session ? 'Thread fortsetzen' : 'Execution oeffnen'),
            currentMarker
        );
    }

    function workflowCardNextMarker(nextMarker) {
        if (!nextMarker.marker_id) {
            return workflowEmptyCard('workflowCardNextMarker', 'Naechster Marker', 'Noch kein naechster Marker gefunden.');
        }

        var meta = [];
        if (nextMarker.plan_title) meta.push(nextMarker.plan_title);
        if (nextMarker.gate_status === 'blocked' && nextMarker.gate_reason) meta.push(nextMarker.gate_reason);
        else if (nextMarker.recommendation_reason) meta.push(nextMarker.recommendation_reason);

        return workflowCardShell(
            'workflowCardNextMarker',
            'Naechster Marker',
            nextMarker.title,
            nextMarker.recommendation_reason || 'Naechster Marker im Handoff.',
            meta,
            nextMarker.gate_status === 'blocked' ? 'Marker pruefen' : 'Execution oeffnen',
            nextMarker
        );
    }

    function workflowCardPendingRatings(pendingRatings) {
        if (!pendingRatings.length) {
            return workflowEmptyCard('workflowCardPendingRatings', 'Abschluesse ohne Rating', 'Keine offenen Ratings.');
        }

        var items = pendingRatings.slice(0, 3).map(function(item) {
            return ''
                + '<div class="workflow-loop-list-item">'
                + '<div>'
                + '<div class="workflow-loop-list-title">' + escapeHtml(item.title) + '</div>'
                + '<div class="workflow-loop-list-meta">' + escapeHtml(item.status_label) + '</div>'
                + '</div>'
                + '<button class="workflow-loop-inline-btn" type="button" onclick="workflowLoopOpenRating(\'' + _escapeJsString(item.plan_id || '') + '\', \'' + _escapeJsString(item.marker_id || '') + '\')">' + escapeHtml(item.cta_label) + '</button>'
                + '</div>';
        }).join('');

        return ''
            + '<article class="workflow-loop-card" id="workflowCardPendingRatings">'
            + '<div class="workflow-loop-card-kicker">Abschluesse ohne Rating</div>'
            + '<div class="workflow-loop-list">' + items + '</div>'
            + '</article>';
    }

    function workflowCardPriorityHints(hints, signals) {
        if (!hints.length) {
            var health = [];
            if (signals.governance_status) health.push('Governance ' + signals.governance_status);
            if (signals.audit_status) health.push('Audit ' + signals.audit_status);
            if (signals.quality_score !== null && signals.quality_score !== undefined) health.push('Quality ' + signals.quality_score);
            return workflowEmptyCard('workflowCardPriorityHints', 'Marker mit Risiko-Hinweisen', health.join(' · ') || 'Keine Risiko-Hinweise.');
        }

        var items = hints.slice(0, 4).map(function(item) {
            return ''
                + '<div class="workflow-loop-list-item">'
                + '<div>'
                + '<div class="workflow-loop-list-title">' + escapeHtml(item.label) + '</div>'
                + '<div class="workflow-loop-list-meta">' + escapeHtml(item.hint) + '</div>'
                + '</div>'
                + '<span class="workflow-loop-level workflow-loop-level--' + escapeHtml(item.level || 'low') + '">' + escapeHtml(item.level || 'low') + '</span>'
                + '</div>';
        }).join('');

        return ''
            + '<article class="workflow-loop-card" id="workflowCardPriorityHints">'
            + '<div class="workflow-loop-card-kicker">Marker mit Risiko-Hinweisen</div>'
            + '<div class="workflow-loop-list">' + items + '</div>'
            + '</article>';
    }

    function workflowCardShell(id, kicker, title, copy, meta, ctaLabel, marker) {
        return ''
            + '<article class="workflow-loop-card" id="' + id + '">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(kicker) + '</div>'
            + '<h3 class="workflow-loop-card-title">' + escapeHtml(title) + '</h3>'
            + '<p class="workflow-loop-card-copy">' + escapeHtml(copy) + '</p>'
            + '<div class="workflow-loop-meta-list">' + (meta || []).map(function(item) {
                return '<div class="workflow-loop-meta-item">' + escapeHtml(item) + '</div>';
            }).join('') + '</div>'
            + '<div class="workflow-loop-card-actions">' + workflowLoopMarkerButtonHtml(ctaLabel, marker) + '</div>'
            + '</article>';
    }

    function workflowEmptyCard(id, kicker, copy) {
        return ''
            + '<article class="workflow-loop-card workflow-loop-card--empty" id="' + id + '">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(kicker) + '</div>'
            + '<p class="workflow-loop-card-copy">' + escapeHtml(copy) + '</p>'
            + '</article>';
    }

    function workflowLoopButtonHtml(ctaLabel, data) {
        if (ctaLabel === 'Planning oeffnen') {
            return '<button class="workflow-loop-cta" type="button" onclick="switchProjectTabByName(\'plans\')">Planning oeffnen</button>';
        }

        var marker = data.current_marker && data.current_marker.marker_id ? data.current_marker : data.next_marker;
        return workflowLoopMarkerButtonHtml(ctaLabel, marker);
    }

    function workflowLoopMarkerButtonHtml(ctaLabel, marker) {
        if (!marker || !marker.plan_id) {
            return '<button class="workflow-loop-inline-btn" type="button" onclick="switchProjectTabByName(\'plans\')">Planning oeffnen</button>';
        }
        var mode = 'chat';
        if (ctaLabel === 'Rating nachholen') mode = 'history';
        var url = workflowLoopCopilotUrl(marker.plan_id, marker.marker_id, mode);
        return '<a class="workflow-loop-inline-btn" href="' + escapeHtml(url) + '">' + escapeHtml(ctaLabel || 'Execution oeffnen') + '</a>';
    }

    function workflowLoopCopilotUrl(planId, markerId, tab) {
        var url = '/copilot?plan_id=' + encodeURIComponent(planId) + '&project=' + encodeURIComponent(PROJECT_NAME);
        if (markerId) url += '&marker_id=' + encodeURIComponent(markerId);
        if (tab) url += '&tab=' + encodeURIComponent(tab);
        return url;
    }

    function handleWorkflowStepClick(step) {
        if (!step) return;
        var cards = {
            gate_ready: 'workflowCardNextMarker',
            active: 'workflowCardCurrentMarker',
            execution: 'workflowCardCurrentMarker',
            write_back: 'workflowCardCurrentMarker',
            rating: 'workflowCardPendingRatings'
        };
        var target = document.getElementById(cards[step.id]);
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function workflowLoopStatusLabel(marker) {
        if (marker.rating_pending) return 'Abschluss unvollstaendig';
        if (marker.status === 'in_progress') return 'Aktiv';
        if (marker.status === 'done') return 'Done';
        if (marker.status === 'blocked') return 'Blocked';
        if (marker.status === 'todo') return 'Todo';
        return marker.status || 'Todo';
    }

    window.loadWorkflowLoop = loadWorkflowLoop;
    window.workflowLoopOpenRating = function(planId, markerId) {
        window.location.href = workflowLoopCopilotUrl(planId, markerId, 'history');
    };
})();
