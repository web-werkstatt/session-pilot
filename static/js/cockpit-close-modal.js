/**
 * Cockpit Close-Modal
 *
 * Marker-Abschluss mit Pflicht-Rating in einem Schritt. Ersetzt den alten
 * getrennten Flow (done setzen -> spaeter rating). Retrospektives Rating
 * gibt es nicht mehr (wertloses Signal, siehe workflow_loop_service
 * RATING_PENDING_WINDOW).
 */
var _cockpitCloseMarkerId = null;

function openCockpitCloseModal(markerId) {
    if (!markerId) return;
    _cockpitCloseMarkerId = markerId;
    document.getElementById('cockpitCloseScore').value = '';
    document.getElementById('cockpitCloseComment').value = '';
    var err = document.getElementById('cockpitCloseError');
    if (err) { err.style.display = 'none'; err.textContent = ''; }
    openModal('cockpitCloseModal');
    setTimeout(function () {
        var sel = document.getElementById('cockpitCloseScore');
        if (sel) sel.focus();
    }, 50);
}

function submitCockpitClose() {
    if (!_cockpitCloseMarkerId) return;
    var scoreRaw = document.getElementById('cockpitCloseScore').value;
    var comment = document.getElementById('cockpitCloseComment').value.trim();
    var errEl = document.getElementById('cockpitCloseError');

    if (scoreRaw === '') {
        if (errEl) { errEl.textContent = 'Bitte einen Score waehlen (0-5).'; errEl.style.display = ''; }
        return;
    }
    var score = Number(scoreRaw);
    if (isNaN(score) || score < 0 || score > 5) {
        if (errEl) { errEl.textContent = 'Ungueltiger Score.'; errEl.style.display = ''; }
        return;
    }

    var btn = document.getElementById('cockpitCloseSubmit');
    if (btn) btn.disabled = true;

    var payload = {
        status: 'done',
        execution_score: score,
        execution_comment: comment
    };
    if (typeof _currentProjectId !== 'undefined' && _currentProjectId) payload.project_id = _currentProjectId;
    if (typeof PLAN_ID !== 'undefined' && PLAN_ID) payload.plan_id = PLAN_ID;

    api.post('/api/copilot/markers/' + encodeURIComponent(_cockpitCloseMarkerId) + '/close', payload)
        .then(function () {
            closeModal('cockpitCloseModal');
            if (typeof _showToast === 'function') _showToast('Marker abgeschlossen und bewertet');
            if (typeof _loadSections === 'function') _loadSections();
            if (typeof _loadMarkerContext === 'function' && _currentSection
                && _currentSection.marker_id === _cockpitCloseMarkerId) {
                _loadMarkerContext(_cockpitCloseMarkerId);
            }
            if (typeof loadCockpitWorkflow === 'function') loadCockpitWorkflow();
            _cockpitCloseMarkerId = null;
        })
        .catch(function (err) {
            var body = err && err.body ? err.body : {};
            var msg = body.message || body.error || (err && err.message) || 'Abschluss fehlgeschlagen';
            if (errEl) { errEl.textContent = msg; errEl.style.display = ''; }
        })
        .finally(function () {
            if (btn) btn.disabled = false;
        });
}

window.openCockpitCloseModal = openCockpitCloseModal;
window.submitCockpitClose = submitCockpitClose;
