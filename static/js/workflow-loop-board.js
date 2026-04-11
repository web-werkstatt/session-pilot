(function() {
    var WL = window.WorkflowLoop = window.WorkflowLoop || {};

    WL.renderBoard = function(container, markerGroups) {
        if (!container) return;

        container.innerHTML = ''
            + '<div class="workflow-loop-board-head">'
            + '<div>'
            + '<div class="workflow-loop-kicker">Operative Steuerung</div>'
            + '<h3 class="workflow-loop-board-title">Marker direkt im Workflow bearbeiten</h3>'
            + '</div>'
            + '<p class="workflow-loop-board-copy">Die Grafik bleibt dein Ueberblick. Darunter steuerst du konkrete Marker: starten, blockieren, Write Back weiterreichen und Ratings abschliessen.</p>'
            + '</div>'
            + markerGroups.map(function(group) {
                return groupHtml(group);
            }).join('')
            + WL.modalShellHtml();

        WL.bindBoard(container);
    };

    function groupHtml(group) {
        var cards = Array.isArray(group.cards) ? group.cards : [];
        return ''
            + '<section class="workflow-marker-group workflow-marker-group--' + escapeHtml(group.tone || 'neutral') + '" id="workflowMarkerGroup-' + escapeHtml(group.id || 'group') + '">'
            + '<div class="workflow-marker-group-head">'
            + '<div>'
            + '<div class="workflow-marker-group-kicker">' + escapeHtml(group.label || 'Marker') + '</div>'
            + '<h4 class="workflow-marker-group-title">' + escapeHtml(groupTitle(group)) + '</h4>'
            + '</div>'
            + '<span class="workflow-marker-group-count">' + cards.length + '</span>'
            + '</div>'
            + (cards.length ? '<div class="workflow-marker-grid">' + cards.map(function(card) {
                return WL.markerCardHtml(card);
            }).join('') + '</div>' : '<div class="workflow-marker-empty">Aktuell keine Marker in diesem Bereich.</div>')
            + '</section>';
    }

    function groupTitle(group) {
        if (group.id === 'active') return 'Laeuft gerade in Execution';
        if (group.id === 'blocked') return 'Braucht eine Begruendung oder Reaktivierung';
        return 'Bereit, geplant oder wartet auf Abschluss';
    }

    WL.markerCardHtml = function(card) {
        var markerId = String(card.marker_id || '');
        var compact = card.group === 'active' && card.workflow_status !== 'blocked' && card.workflow_status !== 'write_back' && card.workflow_status !== 'rating';
        var loading = !!WL.ui.loadingByMarker[markerId];
        var error = WL.ui.errorsByMarker[markerId] || '';
        var success = WL.ui.successByMarker[markerId] || '';
        var messageClass = error ? 'workflow-marker-message workflow-marker-message--error' : (success ? 'workflow-marker-message workflow-marker-message--success' : 'workflow-marker-message');
        var messageText = error || success;
        var meta = [];

        if (compact) {
            return compactCardHtml(card, markerId, loading, messageClass, messageText);
        }

        if (card.plan_title) meta.push(card.plan_title);
        if (card.last_session) meta.push('Session ' + card.last_session);
        if (card.execution_score !== null && card.execution_score !== undefined) meta.push('Execution ' + card.execution_score + '/5');
        if (card.checks_count) meta.push(card.checks_count + ' Checks');
        if (card.gate_status === 'blocked' && card.gate_reason) meta.push('Gate: ' + card.gate_reason);

        return ''
            + '<article class="workflow-marker-card workflow-marker-card--' + escapeHtml(card.group || 'waiting') + (compact ? ' workflow-marker-card--compact' : '') + (card.workflow_status === 'blocked' ? ' is-blocked' : '') + (card.is_current ? ' is-current' : '') + '"'
            + ' data-marker-id="' + escapeHtml(markerId) + '"'
            + ' data-workflow-status="' + escapeHtml(card.workflow_status || '') + '"'
            + ' data-is-current="' + (card.is_current ? '1' : '0') + '"'
            + ' data-is-next="' + (card.is_next ? '1' : '0') + '">'
            + '<div class="workflow-marker-card-top">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(card.workflow_status_label || 'Marker') + '</div>'
            + '</div>'
            + '<h4 class="workflow-marker-card-title">' + escapeHtml(card.title || 'Ohne Titel') + '</h4>'
            + '<p class="workflow-marker-card-copy">' + escapeHtml(WL.markerCopy(card)) + '</p>'
            + (meta.length ? '<div class="workflow-marker-meta">' + meta.map(function(item) {
                return '<span class="workflow-marker-meta-item">' + escapeHtml(item) + '</span>';
            }).join('') + '</div>' : '')
            + WL.actionBarHtml(card, loading)
            + '<div class="' + messageClass + '">' + escapeHtml(messageText) + '</div>'
            + '</article>';
    };

    function compactCardHtml(card, markerId, loading, messageClass, messageText) {
        return ''
            + '<article class="workflow-marker-card workflow-marker-card--' + escapeHtml(card.group || 'waiting') + ' workflow-marker-card--compact' + (card.is_current ? ' is-current' : '') + '"'
            + ' data-marker-id="' + escapeHtml(markerId) + '"'
            + ' data-workflow-status="' + escapeHtml(card.workflow_status || '') + '"'
            + ' data-is-current="' + (card.is_current ? '1' : '0') + '"'
            + ' data-is-next="' + (card.is_next ? '1' : '0') + '">'
            + '<div class="workflow-marker-card-top">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(card.workflow_status_label || 'Aktiv') + '</div>'
            + '</div>'
            + '<h4 class="workflow-marker-card-title">' + escapeHtml(card.title || 'Ohne Titel') + '</h4>'
            + '<div class="workflow-marker-next-step">'
            + '<div class="workflow-marker-next-step-label">Naechster Schritt</div>'
            + '<p class="workflow-marker-card-copy">' + escapeHtml(WL.markerCopy(card)) + '</p>'
            + '</div>'
            + WL.actionBarHtml(card, loading, true)
            + (messageText ? '<div class="' + messageClass + '">' + escapeHtml(messageText) + '</div>' : '')
            + '</article>';
    }

    WL.markerCopy = function(card) {
        if (card.workflow_status === 'blocked' && card.blocked_reason) return card.blocked_reason;
        if (card.next_step) return card.next_step;
        if (card.goal) return card.goal;
        if (card.gate_status === 'blocked' && card.gate_reason) return 'Vor dem Start fehlt noch etwas: ' + card.gate_reason + '.';
        return 'Marker ohne konkreten naechsten Schritt.';
    };

    WL.actionBarHtml = function(card, loading, compact) {
        var buttons = [];
        var allowed = Array.isArray(card.allowed_transitions) ? card.allowed_transitions : [];
        if (compact) {
            if (card.workflow_status === 'active' && allowed.indexOf('write_back') !== -1) {
                buttons.push(WL.actionButton(card, 'write_back', 'An Write Back geben', loading));
            } else if ((card.workflow_status === 'planned' || card.workflow_status === 'ready') && allowed.indexOf('active') !== -1 && card.gate_status === 'ready') {
                buttons.push(WL.actionButton(card, 'start', 'Starten', loading));
            }
            if (allowed.indexOf('blocked') !== -1) {
                buttons.push(WL.actionButton(card, 'block', 'Blockieren', loading, true));
            }
            buttons.push(WL.actionButton(card, 'open_thread', card.last_session ? 'Thread fortsetzen' : 'Execution oeffnen', loading, true));
            return '<div class="workflow-marker-actions workflow-marker-actions--compact">' + buttons.join('') + '</div>';
        }

        if ((card.workflow_status === 'planned' || card.workflow_status === 'ready') && allowed.indexOf('active') !== -1 && card.gate_status === 'ready') {
            buttons.push(WL.actionButton(card, 'start', 'Starten', loading));
        }
        if (allowed.indexOf('blocked') !== -1) {
            buttons.push(WL.actionButton(card, 'block', 'Blockieren', loading, true));
        }
        if (card.workflow_status === 'blocked' && (allowed.indexOf('ready') !== -1 || allowed.indexOf('planned') !== -1 || allowed.indexOf('active') !== -1)) {
            buttons.push(WL.actionButton(card, 'reactivate', 'Reaktivieren', loading));
        }
        if (card.workflow_status === 'active' && allowed.indexOf('write_back') !== -1) {
            buttons.push(WL.actionButton(card, 'write_back', 'An Write Back geben', loading));
        }
        if (card.workflow_status === 'write_back' && allowed.indexOf('rating') !== -1) {
            buttons.push(WL.actionButton(card, 'ready_for_rating', 'Write Back abschliessen', loading));
        }
        if ((card.workflow_status === 'rating' || card.rating_pending)) {
            buttons.push(WL.actionButton(card, 'submit_rating', 'Bewerten', loading));
        }
        buttons.push(WL.actionButton(card, 'details', 'Details', loading, true));
        buttons.push(WL.actionButton(card, 'open_thread', card.last_session ? 'Thread fortsetzen' : 'Execution oeffnen', loading, true));

        return '<div class="workflow-marker-actions">' + buttons.join('') + '</div>';
    };

    WL.actionButton = function(card, action, label, loading, isSecondary) {
        return '<button class="workflow-marker-btn' + (isSecondary ? ' workflow-marker-btn--secondary' : '') + '" type="button" data-action="' + escapeHtml(action) + '" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (loading ? ' disabled' : '') + '>' + escapeHtml(label) + '</button>';
    };
})();
