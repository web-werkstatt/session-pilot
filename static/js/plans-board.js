/**
 * Plans Board — Drag & Drop Logik fuer Workflow-Stage-Spalten.
 * Ausgelagert aus plans.js (Phase 7, 2026-04-14) wegen Dateigroessen-Limit.
 * Nutzt: BOARD_COLUMNS, allPlans, api, showToast (aus plans.js); escapeHtml (base.js).
 */
let _dragPlanId = null;
let _dragSourceStage = null;

function _initBoardDragDrop() {
    // Drag-Start auf Cards
    document.querySelectorAll('.plans-board .plan-card[draggable]').forEach(card => {
        card.addEventListener('dragstart', function(e) {
            _dragPlanId = parseInt(this.dataset.planId);
            _dragSourceStage = this.dataset.stage;
            this.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', _dragPlanId);
        });
        card.addEventListener('dragend', function() {
            this.classList.remove('dragging');
            document.querySelectorAll('.board-column-body.drag-over').forEach(el => el.classList.remove('drag-over'));
            _dragPlanId = null;
            _dragSourceStage = null;
        });
    });

    // Drop-Zonen auf Column-Bodies
    document.querySelectorAll('.board-column-body').forEach(colBody => {
        colBody.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.classList.add('drag-over');
        });
        colBody.addEventListener('dragleave', function(e) {
            // Nur entfernen wenn wirklich verlassen (nicht bei Kind-Elementen)
            if (!this.contains(e.relatedTarget)) {
                this.classList.remove('drag-over');
            }
        });
        colBody.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            const targetStage = this.dataset.stage;
            const planId = parseInt(e.dataTransfer.getData('text/plain'));
            if (!planId || targetStage === _dragSourceStage) return;
            _moveCardToStage(planId, _dragSourceStage, targetStage);
        });
    });
}

function _moveCardToStage(planId, oldStage, newStage) {
    // Optimistisch: Card sofort verschieben
    const card = document.querySelector(`.plan-card[data-plan-id="${planId}"]`);
    const targetCol = document.querySelector(`.board-column-body[data-stage="${newStage}"]`);
    if (card && targetCol) {
        targetCol.appendChild(card);
        card.dataset.stage = newStage;
        // Badge auf Card aktualisieren
        const wfBadge = card.querySelector('.badge-wf');
        if (wfBadge) {
            wfBadge.className = `badge badge-wf badge-wf-${newStage}`;
            wfBadge.textContent = newStage.replace('_', ' ');
        }
        // Column-Counts aktualisieren
        _updateColumnCounts();
    }

    // API-Call
    api.put(`/api/plans/${planId}/workflow`, { workflow_stage: newStage })
        .then(function(result) {
            // Lokale Daten aktualisieren
            const plan = allPlans.find(p => p.id === planId);
            if (plan) {
                plan.workflow_stage = newStage;
                if (result.current_state !== undefined) plan.current_state = result.current_state;
                if (result.target_state !== undefined) plan.target_state = result.target_state;
                if (result.next_action !== undefined) plan.next_action = result.next_action;
            }
            showToast(`Plan in "${_stageLabel(newStage)}" verschoben`);
        })
        .catch(function(err) {
            // Rollback: Card zurueck in alte Spalte
            const sourceCol = document.querySelector(`.board-column-body[data-stage="${oldStage}"]`);
            if (card && sourceCol) {
                sourceCol.appendChild(card);
                card.dataset.stage = oldStage;
                const wfBadge = card.querySelector('.badge-wf');
                if (wfBadge) {
                    wfBadge.className = `badge badge-wf badge-wf-${oldStage}`;
                    wfBadge.textContent = oldStage.replace('_', ' ');
                }
                _updateColumnCounts();
            }
            showToast('Fehler: ' + (err.message || 'Workflow-Update fehlgeschlagen'), true);
        });
}

function _stageLabel(stage) {
    const col = BOARD_COLUMNS.find(c => c.stage === stage);
    return col ? col.label : stage;
}

function _updateColumnCounts() {
    document.querySelectorAll('.board-column').forEach(col => {
        const count = col.querySelectorAll('.plan-card').length;
        const countEl = col.querySelector('.board-count');
        if (countEl) countEl.textContent = count;
    });
}
