(function() {
    var WL = window.WorkflowLoop = window.WorkflowLoop || {};

    WL.bindBoard = function(container) {
        if (!container || container.dataset.bound === '1') return;
        container.dataset.bound = '1';

        container.addEventListener('click', function(event) {
            var actionBtn = event.target.closest('[data-action]');
            var ratingBtn = event.target.closest('[data-rating-score]');

            if (ratingBtn) {
                WL.ui.ratingScores[ratingBtn.getAttribute('data-marker-id')] = ratingBtn.getAttribute('data-rating-score');
                ratingBtn.parentElement.querySelectorAll('.workflow-rating-btn').forEach(function(btn) {
                    btn.classList.toggle('is-active', btn === ratingBtn);
                });
                return;
            }

            if (!actionBtn) return;
            event.preventDefault();
            WL.handleAction(actionBtn.getAttribute('data-action'), actionBtn.getAttribute('data-marker-id'));
        });

        container.addEventListener('input', function(event) {
            var ownerId = event.target.getAttribute('data-owner-input');
            var blockerId = event.target.getAttribute('data-blocker-reason');
            var ratingId = event.target.getAttribute('data-rating-comment');

            if (ownerId) WL.ui.owners[ownerId] = event.target.value;
            if (blockerId) WL.ui.blockerReasons[blockerId] = event.target.value;
            if (ratingId) WL.ui.ratingComments[ratingId] = event.target.value;
        });

        container.addEventListener('change', function(event) {
            var checklistId = event.target.getAttribute('data-marker-id');
            var checklistKey = event.target.getAttribute('data-checklist');
            if (!checklistId || !checklistKey) return;
            var checklist = WL.checklistValue(checklistId);
            checklist[checklistKey] = !!event.target.checked;
            WL.ui.checklists[checklistId] = checklist;
        });
    };

    WL.handleAction = async function(action, markerId) {
        var marker = WL.findMarker(markerId);
        if (!marker) return;

        if (action === 'open_thread') {
            window.location.href = WL.copilotUrl(marker.plan_id, marker.marker_id, marker.last_session ? 'chat' : 'chat');
            return;
        }
        if (action === 'details') {
            WL.openMarkerModal(marker, 'details');
            return;
        }
        if (action === 'block') {
            WL.openMarkerModal(marker, 'block');
            return;
        }
        if (action === 'ready_for_rating') {
            WL.openMarkerModal(marker, 'write_back');
            return;
        }
        if (action === 'submit_rating') {
            WL.openMarkerModal(marker, 'rating');
            return;
        }

        WL.ui.errorsByMarker[markerId] = '';
        WL.ui.successByMarker[markerId] = '';
        WL.ui.loadingByMarker[markerId] = true;
        WL.renderBoard(document.getElementById('workflowLoopBoard'), WL.data.marker_groups || []);

        try {
            if (action === 'start') {
                await api.post('/api/copilot/markers/' + encodeURIComponent(markerId) + '/activate', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    context_path: 'marker-context.md'
                });
                await WL.transition(markerId, 'active', {
                    owner: WL.ownerValue(marker),
                    reason: 'Workflow Loop: Marker gestartet'
                });
                WL.ui.successByMarker[markerId] = 'Marker gestartet.';
            } else if (action === 'save_block') {
                var blockedReason = WL.blockerValue(marker).trim();
                if (!blockedReason) throw new Error('Bitte kurz begruenden, warum der Marker blockiert ist.');
                await api.patch('/api/copilot/markers/' + encodeURIComponent(markerId) + '/status', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    status: 'blocked'
                });
                await WL.transition(markerId, 'blocked', {
                    owner: WL.ownerValue(marker),
                    blocked_reason: blockedReason,
                    reason: 'Workflow Loop: Marker blockiert'
                });
                WL.ui.successByMarker[markerId] = 'Blockierung gespeichert.';
            } else if (action === 'reactivate') {
                var nextStatus = marker.gate_status === 'ready' ? 'ready' : 'planned';
                await api.patch('/api/copilot/markers/' + encodeURIComponent(markerId) + '/status', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    status: 'todo'
                });
                await WL.transition(markerId, nextStatus, {
                    owner: WL.ownerValue(marker),
                    reason: 'Workflow Loop: Marker reaktiviert'
                });
                WL.ui.successByMarker[markerId] = 'Marker reaktiviert.';
            } else if (action === 'write_back') {
                await WL.transition(markerId, 'write_back', {
                    owner: WL.ownerValue(marker),
                    reason: 'Workflow Loop: Write Back gestartet'
                });
                WL.ui.successByMarker[markerId] = 'Write Back offen.';
            } else if (action === 'save_write_back') {
                var checklist = WL.checklistValue(markerId);
                if (!checklist.context || !checklist.result || !checklist.next) {
                    throw new Error('Bitte erst die drei Write-Back-Punkte abhaken.');
                }
                await WL.transition(markerId, 'rating', {
                    owner: WL.ownerValue(marker),
                    reason: 'Workflow Loop: bereit fuer Rating'
                });
                WL.ui.successByMarker[markerId] = 'Marker liegt jetzt im Rating.';
            } else if (action === 'save_rating') {
                var score = Number(WL.ui.ratingScores[markerId] || marker.execution_score || 0);
                if (!score || score < 1 || score > 5) throw new Error('Bitte eine Bewertung von 1 bis 5 auswaehlen.');
                await api.post('/api/marker/' + encodeURIComponent(markerId) + '/execution-rating', {
                    project_id: PROJECT_NAME,
                    plan_id: marker.plan_id,
                    execution_score: score,
                    execution_comment: WL.ui.ratingComments[markerId] || marker.execution_comment || ''
                });
                await WL.transition(markerId, 'done', {
                    owner: WL.ownerValue(marker),
                    reason: 'Workflow Loop: Rating abgeschlossen'
                });
                WL.ui.successByMarker[markerId] = 'Rating gespeichert.';
            }

            WL.ui.loadingByMarker[markerId] = false;
            await loadWorkflowLoop();
        } catch (error) {
            WL.ui.errorsByMarker[markerId] = error && error.message ? error.message : 'Aktion fehlgeschlagen.';
            WL.ui.loadingByMarker[markerId] = false;
            WL.renderBoard(document.getElementById('workflowLoopBoard'), WL.data.marker_groups || []);
        }
    };

    WL.transition = function(markerId, toStatus, extra) {
        return api.post('/api/project/' + encodeURIComponent(PROJECT_NAME) + '/workflow-state/' + encodeURIComponent(markerId) + '/transition', Object.assign({
            to_status: toStatus,
            triggered_by: 'workflow_loop_ui'
        }, extra || {}));
    };

    WL.handleStepClick = function(step) {
        if (!step) return;
        var target = resolveStepTarget(step.id);
        if (!target) return;
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        pulseTarget(target);
    };

    function resolveStepTarget(stepId) {
        if (stepId === 'gate_ready') {
            return document.querySelector('.workflow-marker-card[data-is-next="1"]')
                || document.getElementById('workflowCardNextMarker')
                || document.getElementById('workflowMarkerGroup-waiting');
        }
        if (stepId === 'active' || stepId === 'execution') {
            return document.querySelector('.workflow-marker-card[data-is-current="1"]')
                || document.querySelector('.workflow-marker-card[data-workflow-status="active"]')
                || document.getElementById('workflowCardCurrentMarker')
                || document.getElementById('workflowMarkerGroup-active');
        }
        if (stepId === 'write_back') {
            return document.querySelector('.workflow-marker-card[data-workflow-status="write_back"]')
                || document.getElementById('workflowMarkerGroup-active')
                || document.getElementById('workflowLoopBoard');
        }
        if (stepId === 'rating') {
            return document.querySelector('.workflow-marker-card[data-workflow-status="rating"]')
                || document.getElementById('workflowCardPendingRatings')
                || document.getElementById('workflowMarkerGroup-active');
        }
        return document.getElementById('workflowLoopBoard');
    }

    function pulseTarget(target) {
        if (!target) return;
        target.classList.remove('workflow-loop-target-pulse');
        void target.offsetWidth;
        target.classList.add('workflow-loop-target-pulse');
        window.setTimeout(function() {
            target.classList.remove('workflow-loop-target-pulse');
        }, 1600);
    }
})();
