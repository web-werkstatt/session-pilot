(function() {
    var workflowLoopData = null;
    var workflowLoopUi = {
        loadingByMarker: {},
        errorsByMarker: {},
        successByMarker: {},
        owners: {},
        blockerReasons: {},
        ratingScores: {},
        ratingComments: {},
        checklists: {}
    };

    function workflowLoopEscapeJsString(text) {
        return String(text || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    }

    function ensureWorkflowLoopLayout(shell) {
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

    async function loadWorkflowLoop() {
        var shell = document.getElementById('workflowLoopShell');
        if (!shell) return;

        shell.classList.remove('is-error');
        shell.classList.remove('is-empty');
        shell.setAttribute('aria-busy', 'true');

        try {
            ensureWorkflowLoopLayout(shell);
            workflowLoopData = await api.get('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/workflow-loop');
            renderWorkflowLoop(shell, workflowLoopData || {});
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

        renderWorkflowSummary(summary, data);
        renderWorkflowCards(cards, data);
        renderWorkflowBoard(board, markerGroups);
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

    function renderWorkflowBoard(container, markerGroups) {
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
                return workflowLoopGroupHtml(group);
            }).join('');

        bindWorkflowBoard(container);
    }

    function workflowLoopGroupHtml(group) {
        var cards = Array.isArray(group.cards) ? group.cards : [];
        return ''
            + '<section class="workflow-marker-group workflow-marker-group--' + escapeHtml(group.tone || 'neutral') + '">'
            + '<div class="workflow-marker-group-head">'
            + '<div>'
            + '<div class="workflow-marker-group-kicker">' + escapeHtml(group.label || 'Marker') + '</div>'
            + '<h4 class="workflow-marker-group-title">' + escapeHtml(workflowGroupTitle(group)) + '</h4>'
            + '</div>'
            + '<span class="workflow-marker-group-count">' + cards.length + '</span>'
            + '</div>'
            + (cards.length ? '<div class="workflow-marker-grid">' + cards.map(function(card) {
                return workflowMarkerCardHtml(card);
            }).join('') + '</div>' : '<div class="workflow-marker-empty">Aktuell keine Marker in diesem Bereich.</div>')
            + '</section>';
    }

    function workflowGroupTitle(group) {
        if (group.id === 'active') return 'Laeuft gerade oder braucht unmittelbaren Abschluss';
        if (group.id === 'blocked') return 'Braucht eine Begruendung oder Reaktivierung';
        return 'Bereit, geplant oder sauber abgeschlossen';
    }

    function workflowMarkerCardHtml(card) {
        var markerId = String(card.marker_id || '');
        var owner = workflowLoopOwnerValue(card);
        var loading = !!workflowLoopUi.loadingByMarker[markerId];
        var error = workflowLoopUi.errorsByMarker[markerId] || '';
        var success = workflowLoopUi.successByMarker[markerId] || '';
        var messageClass = error ? 'workflow-marker-message workflow-marker-message--error' : (success ? 'workflow-marker-message workflow-marker-message--success' : 'workflow-marker-message');
        var messageText = error || success;
        var meta = [];

        if (card.plan_title) meta.push(card.plan_title);
        if (card.last_session) meta.push('Session ' + card.last_session);
        if (card.execution_score !== null && card.execution_score !== undefined) meta.push('Execution ' + card.execution_score + '/5');
        if (card.checks_count) meta.push(card.checks_count + ' Checks');
        if (card.gate_status === 'blocked' && card.gate_reason) meta.push('Gate: ' + card.gate_reason);

        return ''
            + '<article class="workflow-marker-card workflow-marker-card--' + escapeHtml(card.group || 'waiting') + (card.workflow_status === 'blocked' ? ' is-blocked' : '') + (card.is_current ? ' is-current' : '') + '" data-marker-id="' + escapeHtml(markerId) + '">'
            + '<div class="workflow-marker-card-top">'
            + '<div class="workflow-loop-card-kicker">' + escapeHtml(card.workflow_status_label || 'Marker') + '</div>'
            + workflowOwnerBadgeHtml(owner)
            + '</div>'
            + '<div class="workflow-marker-card-flags">' + workflowMarkerFlagsHtml(card) + '</div>'
            + '<h4 class="workflow-marker-card-title">' + escapeHtml(card.title || 'Ohne Titel') + '</h4>'
            + '<p class="workflow-marker-card-copy">' + escapeHtml(workflowMarkerCopy(card)) + '</p>'
            + '<div class="workflow-marker-meta">' + meta.map(function(item) {
                return '<span class="workflow-marker-meta-item">' + escapeHtml(item) + '</span>';
            }).join('') + '</div>'
            + workflowMarkerFocusHtml(card)
            + workflowMarkerEditorHtml(card)
            + workflowMarkerActionBarHtml(card, loading)
            + '<div class="' + messageClass + '">' + escapeHtml(messageText) + '</div>'
            + '</article>';
    }

    function workflowOwnerBadgeHtml(owner) {
        var label = owner || 'Kein Owner';
        var initial = (owner || '?').charAt(0).toUpperCase();
        return ''
            + '<div class="workflow-owner-badge' + (owner ? '' : ' workflow-owner-badge--empty') + '">'
            + '<span class="workflow-owner-badge-dot">' + escapeHtml(initial) + '</span>'
            + '<span class="workflow-owner-badge-label">' + escapeHtml(label) + '</span>'
            + '</div>';
    }

    function workflowMarkerFlagsHtml(card) {
        var flags = [];
        if (card.is_current) flags.push('<span class="workflow-marker-flag workflow-marker-flag--current">Laeuft jetzt</span>');
        if (card.is_next) flags.push('<span class="workflow-marker-flag workflow-marker-flag--next">Als naechstes</span>');
        if (card.rating_pending) flags.push('<span class="workflow-marker-flag workflow-marker-flag--rating">Rating offen</span>');
        if (card.gate_status === 'blocked') flags.push('<span class="workflow-marker-flag workflow-marker-flag--blocked">Gate blockiert</span>');
        return flags.join('');
    }

    function workflowMarkerCopy(card) {
        if (card.workflow_status === 'blocked' && card.blocked_reason) return card.blocked_reason;
        if (card.next_step) return card.next_step;
        if (card.goal) return card.goal;
        if (card.gate_status === 'blocked' && card.gate_reason) return 'Vor dem Start fehlt noch etwas: ' + card.gate_reason + '.';
        return 'Marker ohne konkreten naechsten Schritt.';
    }

    function workflowMarkerFocusHtml(card) {
        if (card.workflow_status === 'write_back') {
            return workflowWriteBackHtml(card);
        }
        if (card.workflow_status === 'rating' || card.rating_pending) {
            return workflowRatingHtml(card);
        }
        if (card.workflow_status === 'blocked') {
            return workflowBlockedHtml(card);
        }
        return '';
    }

    function workflowWriteBackHtml(card) {
        var checklist = workflowLoopChecklistValue(card.marker_id);
        return ''
            + '<div class="workflow-marker-focus workflow-marker-focus--writeback">'
            + '<div class="workflow-marker-focus-title">Write Back abschliessen</div>'
            + '<label class="workflow-checklist-item"><input type="checkbox" data-checklist="context" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (checklist.context ? ' checked' : '') + '> Kontext aktualisiert</label>'
            + '<label class="workflow-checklist-item"><input type="checkbox" data-checklist="result" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (checklist.result ? ' checked' : '') + '> Ergebnis in Marker oder Session dokumentiert</label>'
            + '<label class="workflow-checklist-item"><input type="checkbox" data-checklist="next" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (checklist.next ? ' checked' : '') + '> Naechsten Schritt sauber hinterlegt</label>'
            + '</div>';
    }

    function workflowRatingHtml(card) {
        var markerId = String(card.marker_id || '');
        var activeScore = String(workflowLoopUi.ratingScores[markerId] || card.execution_score || '');
        var comment = workflowLoopUi.ratingComments[markerId];
        if (comment === undefined || comment === null) comment = card.execution_comment || '';
        return ''
            + '<div class="workflow-marker-focus workflow-marker-focus--rating">'
            + '<div class="workflow-marker-focus-title">Execution bewerten</div>'
            + '<div class="workflow-rating-scale">' + [1, 2, 3, 4, 5].map(function(score) {
                var isActive = activeScore === String(score);
                return '<button class="workflow-rating-btn' + (isActive ? ' is-active' : '') + '" type="button" data-rating-score="' + score + '" data-marker-id="' + escapeHtml(markerId) + '">' + score + '</button>';
            }).join('') + '</div>'
            + '<textarea class="workflow-marker-textarea" data-rating-comment="' + escapeHtml(markerId) + '" rows="3" placeholder="Kurz festhalten, wie gut der Marker abgeschlossen wurde.">' + escapeHtml(comment) + '</textarea>'
            + '</div>';
    }

    function workflowBlockedHtml(card) {
        var markerId = String(card.marker_id || '');
        var reason = workflowLoopBlockerValue(card);
        return ''
            + '<div class="workflow-marker-focus workflow-marker-focus--blocked">'
            + '<div class="workflow-marker-focus-title">Warum ist der Marker blockiert?</div>'
            + '<textarea class="workflow-marker-textarea workflow-marker-textarea--danger" data-blocker-reason="' + escapeHtml(markerId) + '" rows="3" placeholder="Kurze Begruendung, damit die Blockierung fuer andere nachvollziehbar bleibt.">' + escapeHtml(reason) + '</textarea>'
            + '</div>';
    }

    function workflowMarkerEditorHtml(card) {
        return ''
            + '<div class="workflow-marker-editor">'
            + '<label class="workflow-marker-editor-label">Owner</label>'
            + '<input class="workflow-marker-owner-input" type="text" data-owner-input="' + escapeHtml(card.marker_id) + '" value="' + escapeHtml(workflowLoopOwnerValue(card)) + '" placeholder="z. B. Joshko">'
            + '</div>';
    }

    function workflowMarkerActionBarHtml(card, loading) {
        var buttons = [];
        var allowed = Array.isArray(card.allowed_transitions) ? card.allowed_transitions : [];
        if ((card.workflow_status === 'planned' || card.workflow_status === 'ready') && allowed.indexOf('active') !== -1 && card.gate_status === 'ready') {
            buttons.push(workflowActionButton(card, 'start', 'Starten', loading));
        }
        if (allowed.indexOf('blocked') !== -1) {
            buttons.push(workflowActionButton(card, 'block', 'Blockieren', loading));
        }
        if (card.workflow_status === 'blocked' && (allowed.indexOf('ready') !== -1 || allowed.indexOf('planned') !== -1 || allowed.indexOf('active') !== -1)) {
            buttons.push(workflowActionButton(card, 'reactivate', 'Reaktivieren', loading));
        }
        if (card.workflow_status === 'active' && allowed.indexOf('write_back') !== -1) {
            buttons.push(workflowActionButton(card, 'write_back', 'An Write Back geben', loading));
        }
        if (card.workflow_status === 'write_back' && allowed.indexOf('rating') !== -1) {
            buttons.push(workflowActionButton(card, 'ready_for_rating', 'An Rating uebergeben', loading));
        }
        if ((card.workflow_status === 'rating' || card.rating_pending)) {
            buttons.push(workflowActionButton(card, 'submit_rating', 'Rating speichern', loading));
        }
        buttons.push(workflowActionButton(card, 'open_thread', card.last_session ? 'Thread fortsetzen' : 'Execution oeffnen', loading, true));

        return '<div class="workflow-marker-actions">' + buttons.join('') + '</div>';
    }

    function workflowActionButton(card, action, label, loading, isSecondary) {
        return '<button class="workflow-marker-btn' + (isSecondary ? ' workflow-marker-btn--secondary' : '') + '" type="button" data-action="' + escapeHtml(action) + '" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (loading ? ' disabled' : '') + '>' + escapeHtml(label) + '</button>';
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
                + '<button class="workflow-loop-inline-btn" type="button" onclick="workflowLoopOpenRating(\'' + workflowLoopEscapeJsString(item.plan_id || '') + '\', \'' + workflowLoopEscapeJsString(item.marker_id || '') + '\')">' + escapeHtml(item.cta_label) + '</button>'
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

    function bindWorkflowBoard(container) {
        if (!container || container.dataset.bound === '1') return;
        container.dataset.bound = '1';

        container.addEventListener('click', function(event) {
            var actionBtn = event.target.closest('[data-action]');
            var ratingBtn = event.target.closest('[data-rating-score]');

            if (ratingBtn) {
                workflowLoopUi.ratingScores[ratingBtn.getAttribute('data-marker-id')] = ratingBtn.getAttribute('data-rating-score');
                renderWorkflowBoard(container, workflowLoopData.marker_groups || []);
                return;
            }

            if (!actionBtn) return;
            event.preventDefault();
            workflowLoopHandleAction(actionBtn.getAttribute('data-action'), actionBtn.getAttribute('data-marker-id'));
        });

        container.addEventListener('input', function(event) {
            var ownerId = event.target.getAttribute('data-owner-input');
            var blockerId = event.target.getAttribute('data-blocker-reason');
            var ratingId = event.target.getAttribute('data-rating-comment');

            if (ownerId) workflowLoopUi.owners[ownerId] = event.target.value;
            if (blockerId) workflowLoopUi.blockerReasons[blockerId] = event.target.value;
            if (ratingId) workflowLoopUi.ratingComments[ratingId] = event.target.value;
        });

        container.addEventListener('change', function(event) {
            var checklistId = event.target.getAttribute('data-marker-id');
            var checklistKey = event.target.getAttribute('data-checklist');
            if (!checklistId || !checklistKey) return;
            var checklist = workflowLoopChecklistValue(checklistId);
            checklist[checklistKey] = !!event.target.checked;
            workflowLoopUi.checklists[checklistId] = checklist;
        });
    }

    async function workflowLoopHandleAction(action, markerId) {
        var marker = workflowLoopFindMarker(markerId);
        if (!marker) return;

        if (action === 'open_thread') {
            window.location.href = workflowLoopCopilotUrl(marker.plan_id, marker.marker_id, marker.last_session ? 'chat' : 'chat');
            return;
        }

        workflowLoopUi.errorsByMarker[markerId] = '';
        workflowLoopUi.successByMarker[markerId] = '';
        workflowLoopUi.loadingByMarker[markerId] = true;
        renderWorkflowBoard(document.getElementById('workflowLoopBoard'), workflowLoopData.marker_groups || []);

        try {
            if (action === 'start') {
                await api.post('/api/copilot/markers/' + encodeURIComponent(markerId) + '/activate', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    context_path: 'marker-context.md'
                });
                await workflowLoopTransition(markerId, 'active', {
                    owner: workflowLoopOwnerValue(marker),
                    reason: 'Workflow Loop: Marker gestartet'
                });
                workflowLoopUi.successByMarker[markerId] = 'Marker gestartet.';
            } else if (action === 'block') {
                var blockedReason = workflowLoopBlockerValue(marker).trim();
                if (!blockedReason) throw new Error('Bitte kurz begruenden, warum der Marker blockiert ist.');
                await api.patch('/api/copilot/markers/' + encodeURIComponent(markerId) + '/status', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    status: 'blocked'
                });
                await workflowLoopTransition(markerId, 'blocked', {
                    owner: workflowLoopOwnerValue(marker),
                    blocked_reason: blockedReason,
                    reason: 'Workflow Loop: Marker blockiert'
                });
                workflowLoopUi.successByMarker[markerId] = 'Blockierung gespeichert.';
            } else if (action === 'reactivate') {
                var nextStatus = marker.gate_status === 'ready' ? 'ready' : 'planned';
                await api.patch('/api/copilot/markers/' + encodeURIComponent(markerId) + '/status', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    status: 'todo'
                });
                await workflowLoopTransition(markerId, nextStatus, {
                    owner: workflowLoopOwnerValue(marker),
                    reason: 'Workflow Loop: Marker reaktiviert'
                });
                workflowLoopUi.successByMarker[markerId] = 'Marker reaktiviert.';
            } else if (action === 'write_back') {
                await workflowLoopTransition(markerId, 'write_back', {
                    owner: workflowLoopOwnerValue(marker),
                    reason: 'Workflow Loop: Write Back gestartet'
                });
                workflowLoopUi.successByMarker[markerId] = 'Write Back offen.';
            } else if (action === 'ready_for_rating') {
                var checklist = workflowLoopChecklistValue(markerId);
                if (!checklist.context || !checklist.result || !checklist.next) {
                    throw new Error('Bitte erst die drei Write-Back-Punkte abhaken.');
                }
                await workflowLoopTransition(markerId, 'rating', {
                    owner: workflowLoopOwnerValue(marker),
                    reason: 'Workflow Loop: bereit fuer Rating'
                });
                workflowLoopUi.successByMarker[markerId] = 'Marker liegt jetzt im Rating.';
            } else if (action === 'submit_rating') {
                var score = Number(workflowLoopUi.ratingScores[markerId] || marker.execution_score || 0);
                if (!score || score < 1 || score > 5) throw new Error('Bitte eine Bewertung von 1 bis 5 auswaehlen.');
                await api.post('/api/marker/' + encodeURIComponent(markerId) + '/execution-rating', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    execution_score: score,
                    execution_comment: workflowLoopUi.ratingComments[markerId] || marker.execution_comment || ''
                });
                await workflowLoopTransition(markerId, 'done', {
                    owner: workflowLoopOwnerValue(marker),
                    reason: 'Workflow Loop: Rating abgeschlossen'
                });
                workflowLoopUi.successByMarker[markerId] = 'Rating gespeichert.';
            }

            workflowLoopUi.loadingByMarker[markerId] = false;
            await loadWorkflowLoop();
        } catch (error) {
            workflowLoopUi.errorsByMarker[markerId] = error && error.message ? error.message : 'Aktion fehlgeschlagen.';
            workflowLoopUi.loadingByMarker[markerId] = false;
            renderWorkflowBoard(document.getElementById('workflowLoopBoard'), workflowLoopData.marker_groups || []);
        }
    }

    async function workflowLoopTransition(markerId, toStatus, extra) {
        return api.post('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/workflow-state/' + encodeURIComponent(markerId) + '/transition', Object.assign({
            to_status: toStatus,
            triggered_by: 'workflow_loop_ui'
        }, extra || {}));
    }

    function workflowLoopFindMarker(markerId) {
        if (!workflowLoopData || !Array.isArray(workflowLoopData.marker_groups)) return null;
        for (var i = 0; i < workflowLoopData.marker_groups.length; i += 1) {
            var group = workflowLoopData.marker_groups[i];
            var cards = Array.isArray(group.cards) ? group.cards : [];
            for (var j = 0; j < cards.length; j += 1) {
                if (String(cards[j].marker_id) === String(markerId)) return cards[j];
            }
        }
        return null;
    }

    function workflowLoopOwnerValue(card) {
        var markerId = String(card.marker_id || '');
        if (workflowLoopUi.owners[markerId] !== undefined) return workflowLoopUi.owners[markerId];
        return card.owner || '';
    }

    function workflowLoopBlockerValue(card) {
        var markerId = String(card.marker_id || '');
        if (workflowLoopUi.blockerReasons[markerId] !== undefined) return workflowLoopUi.blockerReasons[markerId];
        return card.blocked_reason || '';
    }

    function workflowLoopChecklistValue(markerId) {
        markerId = String(markerId || '');
        if (!workflowLoopUi.checklists[markerId]) {
            workflowLoopUi.checklists[markerId] = { context: false, result: false, next: false };
        }
        return workflowLoopUi.checklists[markerId];
    }

    function handleWorkflowStepClick(step) {
        if (!step) return;
        var cards = {
            gate_ready: 'workflowCardNextMarker',
            active: 'workflowCardCurrentMarker',
            execution: 'workflowCardCurrentMarker',
            write_back: 'workflowLoopBoard',
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
