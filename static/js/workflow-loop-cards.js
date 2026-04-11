(function() {
    var WL = window.WorkflowLoop = window.WorkflowLoop || {};

    WL.renderSummary = function(container, data) {
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
        if (currentMarker.status) pills.push(WL.statusLabel(currentMarker));
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
            + WL.summaryButtonHtml(ctaLabel, data)
            + '</div>';
    };

    WL.renderCards = function(container, data) {
        if (!container) return;

        var currentMarker = data.current_marker || {};
        var nextMarker = data.next_marker || {};
        var pendingRatings = Array.isArray(data.pending_ratings) ? data.pending_ratings : [];
        var hints = data.signals && Array.isArray(data.signals.priority_hints) ? data.signals.priority_hints : [];

        container.innerHTML = ''
            + cardCurrentMarker(currentMarker)
            + cardNextMarker(nextMarker)
            + cardPendingRatings(pendingRatings)
            + cardPriorityHints(hints, data.signals || {});
    };

    function cardCurrentMarker(currentMarker) {
        if (!currentMarker.marker_id) {
            return emptyCard('workflowCardCurrentMarker', 'Aktiver Marker', 'Aktuell laeuft kein aktiver Marker.');
        }

        var meta = [];
        if (currentMarker.last_session) meta.push('Session ' + currentMarker.last_session);
        if (currentMarker.execution_score !== null && currentMarker.execution_score !== undefined) meta.push('Execution ' + currentMarker.execution_score + '/5');
        if (currentMarker.gate_status === 'blocked' && currentMarker.gate_reason) meta.push(currentMarker.gate_reason);

        return cardShell(
            'workflowCardCurrentMarker',
            'Aktiver Marker',
            currentMarker.title,
            currentMarker.next_step || WL.statusLabel(currentMarker),
            meta,
            currentMarker.rating_pending ? 'Rating nachholen' : (currentMarker.last_session ? 'Thread fortsetzen' : 'Execution oeffnen'),
            currentMarker
        );
    }

    function cardNextMarker(nextMarker) {
        if (!nextMarker.marker_id) {
            return emptyCard('workflowCardNextMarker', 'Naechster Marker', 'Noch kein naechster Marker gefunden.');
        }

        var meta = [];
        if (nextMarker.plan_title) meta.push(nextMarker.plan_title);
        if (nextMarker.gate_status === 'blocked' && nextMarker.gate_reason) meta.push(nextMarker.gate_reason);
        else if (nextMarker.recommendation_reason) meta.push(nextMarker.recommendation_reason);

        return cardShell(
            'workflowCardNextMarker',
            'Naechster Marker',
            nextMarker.title,
            nextMarker.recommendation_reason || 'Naechster Marker im Handoff.',
            meta,
            nextMarker.gate_status === 'blocked' ? 'Marker pruefen' : 'Execution oeffnen',
            nextMarker
        );
    }

    function cardPendingRatings(pendingRatings) {
        if (!pendingRatings.length) {
            return emptyCard('workflowCardPendingRatings', 'Abschluesse ohne Rating', 'Keine offenen Ratings.');
        }

        var items = pendingRatings.slice(0, 3).map(function(item) {
            return ''
                + '<div class="workflow-loop-list-item">'
                + '<div>'
                + '<div class="workflow-loop-list-title">' + escapeHtml(item.title) + '</div>'
                + '<div class="workflow-loop-list-meta">' + escapeHtml(item.status_label) + '</div>'
                + '</div>'
                + '<button class="workflow-loop-inline-btn" type="button" onclick="workflowLoopOpenRating(\'' + WL.escapeJsString(item.plan_id || '') + '\', \'' + WL.escapeJsString(item.marker_id || '') + '\')">' + escapeHtml(item.cta_label) + '</button>'
                + '</div>';
        }).join('');

        return ''
            + '<article class="workflow-loop-card" id="workflowCardPendingRatings">'
            + '<div class="workflow-loop-card-kicker">Abschluesse ohne Rating</div>'
            + '<div class="workflow-loop-list">' + items + '</div>'
            + '</article>';
    }

    function cardPriorityHints(hints, signals) {
        if (!hints.length) {
            var health = [];
            if (signals.governance_status) health.push('Governance ' + signals.governance_status);
            if (signals.audit_status) health.push('Audit ' + signals.audit_status);
            if (signals.quality_score !== null && signals.quality_score !== undefined) health.push('Quality ' + signals.quality_score);
            return emptyCard('workflowCardPriorityHints', 'Marker mit Risiko-Hinweisen', health.join(' · ') || 'Keine Risiko-Hinweise.');
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

    function cardShell(id, kicker, title, copy, meta, ctaLabel, marker) {
        return ''
            + '<article class="workflow-loop-card" id="' + id + '">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(kicker) + '</div>'
            + '<h3 class="workflow-loop-card-title">' + escapeHtml(title) + '</h3>'
            + '<p class="workflow-loop-card-copy">' + escapeHtml(copy) + '</p>'
            + '<div class="workflow-loop-meta-list">' + (meta || []).map(function(item) {
                return '<div class="workflow-loop-meta-item">' + escapeHtml(item) + '</div>';
            }).join('') + '</div>'
            + '<div class="workflow-loop-card-actions">' + WL.markerButtonHtml(ctaLabel, marker) + '</div>'
            + '</article>';
    }

    function emptyCard(id, kicker, copy) {
        return ''
            + '<article class="workflow-loop-card workflow-loop-card--empty" id="' + id + '">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(kicker) + '</div>'
            + '<p class="workflow-loop-card-copy">' + escapeHtml(copy) + '</p>'
            + '</article>';
    }

    WL.summaryButtonHtml = function(ctaLabel, data) {
        if (ctaLabel === 'Planning oeffnen') {
            return '<button class="workflow-loop-cta" type="button" onclick="switchProjectTabByName(\'plans\')">Planning oeffnen</button>';
        }
        var marker = data.current_marker && data.current_marker.marker_id ? data.current_marker : data.next_marker;
        return WL.markerButtonHtml(ctaLabel, marker);
    };

    WL.markerButtonHtml = function(ctaLabel, marker) {
        if (!marker || !marker.plan_id) {
            return '<button class="workflow-loop-inline-btn" type="button" onclick="switchProjectTabByName(\'plans\')">Planning oeffnen</button>';
        }
        var mode = 'chat';
        if (ctaLabel === 'Rating nachholen') mode = 'history';
        var url = WL.copilotUrl(marker.plan_id, marker.marker_id, mode);
        return '<a class="workflow-loop-inline-btn" href="' + escapeHtml(url) + '">' + escapeHtml(ctaLabel || 'Execution oeffnen') + '</a>';
    };
})();
