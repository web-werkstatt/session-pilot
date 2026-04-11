(function() {
    var WL = window.WorkflowLoop = window.WorkflowLoop || {};

    WL.modalShellHtml = function() {
        return ''
            + '<div class="modal-overlay workflow-marker-modal-overlay" id="workflowMarkerModal">'
            + '<div class="modal-content workflow-marker-modal">'
            + '<div class="modal-header workflow-marker-modal-head">'
            + '<div>'
            + '<div class="workflow-loop-card-kicker" id="workflowMarkerModalKicker">Marker</div>'
            + '<h2 id="workflowMarkerModalTitle">Marker</h2>'
            + '</div>'
            + '<button class="modal-close" type="button" onclick="closeModal(\'workflowMarkerModal\')">&times;</button>'
            + '</div>'
            + '<div class="modal-body workflow-marker-modal-body" id="workflowMarkerModalBody"></div>'
            + '</div>'
            + '</div>';
    };

    WL.openMarkerModal = function(card, mode) {
        var modal = document.getElementById('workflowMarkerModal');
        var title = document.getElementById('workflowMarkerModalTitle');
        var kicker = document.getElementById('workflowMarkerModalKicker');
        var body = document.getElementById('workflowMarkerModalBody');
        if (!modal || !title || !kicker || !body) return;
        title.textContent = card.title || 'Ohne Titel';
        kicker.textContent = card.workflow_status_label || 'Marker';
        body.innerHTML = modalHtml(card, mode || 'details');
        openModal('workflowMarkerModal');
    };

    function modalHtml(card, mode) {
        var meta = [];
        if (card.plan_title) meta.push(card.plan_title);
        if (card.last_session) meta.push('Session ' + card.last_session);
        if (card.execution_score !== null && card.execution_score !== undefined) meta.push('Execution ' + card.execution_score + '/5');
        if (card.checks_count) meta.push(card.checks_count + ' Checks');
        var detail = ''
            + '<div class="workflow-marker-modal-section">'
            + '<div class="workflow-marker-modal-label">Naechster Schritt</div>'
            + '<p>' + escapeHtml(WL.markerCopy(card)) + '</p>'
            + '</div>'
            + (meta.length ? '<div class="workflow-marker-meta workflow-marker-modal-meta">' + meta.map(function(item) {
                return '<span class="workflow-marker-meta-item">' + escapeHtml(item) + '</span>';
            }).join('') + '</div>' : '');

        if (mode === 'block') {
            return detail + blockedHtml(card, 'Blockierung speichern');
        }
        if (mode === 'write_back' || card.workflow_status === 'write_back') {
            return detail + writeBackHtml(card, 'Write Back abschliessen');
        }
        if (mode === 'rating' || card.workflow_status === 'rating' || card.rating_pending) {
            return detail + ratingHtml(card, 'Rating speichern');
        }
        return detail;
    }

    function writeBackHtml(card, actionLabel) {
        var checklist = WL.checklistValue(card.marker_id);
        return ''
            + '<div class="workflow-marker-focus workflow-marker-focus--writeback">'
            + '<div class="workflow-marker-focus-title">Write Back abschliessen</div>'
            + '<label class="workflow-checklist-item"><input type="checkbox" data-checklist="context" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (checklist.context ? ' checked' : '') + '> Kontext aktualisiert</label>'
            + '<label class="workflow-checklist-item"><input type="checkbox" data-checklist="result" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (checklist.result ? ' checked' : '') + '> Ergebnis in Marker oder Session dokumentiert</label>'
            + '<label class="workflow-checklist-item"><input type="checkbox" data-checklist="next" data-marker-id="' + escapeHtml(card.marker_id) + '"' + (checklist.next ? ' checked' : '') + '> Naechsten Schritt sauber hinterlegt</label>'
            + (actionLabel ? '<div class="workflow-marker-modal-actions">' + WL.actionButton(card, 'save_write_back', actionLabel, false) + '</div>' : '')
            + '</div>';
    }

    function ratingHtml(card, actionLabel) {
        var markerId = String(card.marker_id || '');
        var activeScore = String(WL.ui.ratingScores[markerId] || card.execution_score || '');
        var comment = WL.ui.ratingComments[markerId];
        if (comment === undefined || comment === null) comment = card.execution_comment || '';
        return ''
            + '<div class="workflow-marker-focus workflow-marker-focus--rating">'
            + '<div class="workflow-marker-focus-title">Execution bewerten</div>'
            + '<div class="workflow-rating-scale">' + [1, 2, 3, 4, 5].map(function(score) {
                var isActive = activeScore === String(score);
                return '<button class="workflow-rating-btn' + (isActive ? ' is-active' : '') + '" type="button" data-rating-score="' + score + '" data-marker-id="' + escapeHtml(markerId) + '">' + score + '</button>';
            }).join('') + '</div>'
            + '<textarea class="workflow-marker-textarea" data-rating-comment="' + escapeHtml(markerId) + '" rows="3" placeholder="Kurz festhalten, wie gut der Marker abgeschlossen wurde.">' + escapeHtml(comment) + '</textarea>'
            + (actionLabel ? '<div class="workflow-marker-modal-actions">' + WL.actionButton(card, 'save_rating', actionLabel, false) + '</div>' : '')
            + '</div>';
    }

    function blockedHtml(card, actionLabel) {
        var markerId = String(card.marker_id || '');
        var reason = WL.blockerValue(card);
        return ''
            + '<div class="workflow-marker-focus workflow-marker-focus--blocked">'
            + '<div class="workflow-marker-focus-title">Warum ist der Marker blockiert?</div>'
            + '<textarea class="workflow-marker-textarea workflow-marker-textarea--danger" data-blocker-reason="' + escapeHtml(markerId) + '" rows="3" placeholder="Kurze Begruendung, damit die Blockierung fuer andere nachvollziehbar bleibt.">' + escapeHtml(reason) + '</textarea>'
            + (actionLabel ? '<div class="workflow-marker-modal-actions">' + WL.actionButton(card, 'save_block', actionLabel, false) + '</div>' : '')
            + '</div>';
    }
})();
