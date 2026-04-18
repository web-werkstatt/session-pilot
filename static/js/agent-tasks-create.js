/**
 * Agent Task Create Modal
 * Sprint sprint-agent-orchestrator-soll-workflow-luecken Session L2 (2026-04-18):
 * "Neuer Task"-Button auf /agent-tasks mit Modal zum Anlegen.
 *
 * required_verification-Mapping identisch zum CLI (scripts/claude_task_io.py,
 * ALLOWED_VERIFY_CLAIMS + CLAIM_TO_VERIFY_TYPE), damit UI- und CLI-Payload
 * deckungsgleich sind (AC-L2-4).
 */

var _agentTaskClaimToType = {
    "tests_passed": "command_exit_zero",
    "append_only_respected": "append_only_diff",
    "docs_updated": "docs_updated",
    "feature_complete": "feature_complete"
};

function openAgentTaskCreateModal() {
    document.getElementById('agentTaskCreateTitle').value = '';
    document.getElementById('agentTaskCreateGoal').value = '';
    document.getElementById('agentTaskCreateAllowed').value = '';
    document.getElementById('agentTaskCreateProjectId').value = '';
    document.getElementById('agentTaskCreateMarkerId').value = '';
    document.getElementById('agentTaskCreateTestsCommand').value = 'pytest -q';
    var errEl = document.getElementById('agentTaskCreateError');
    if (errEl) { errEl.style.display = 'none'; errEl.textContent = ''; }
    var boxes = document.querySelectorAll('.agent-task-create-verify');
    for (var i = 0; i < boxes.length; i++) boxes[i].checked = false;
    _agentTaskCreateToggleTestsCommand();
    openModal('agentTaskCreateModal');
    setTimeout(function() {
        var t = document.getElementById('agentTaskCreateTitle');
        if (t) t.focus();
    }, 50);
}

function _agentTaskCreateToggleTestsCommand() {
    var testsBox = document.getElementById('agentTaskCreateVerifyTests');
    var cmdWrap = document.getElementById('agentTaskCreateTestsCommandWrap');
    if (!testsBox || !cmdWrap) return;
    cmdWrap.style.display = testsBox.checked ? '' : 'none';
}

function _agentTaskCreateBuildVerification() {
    var entries = [];
    var boxes = document.querySelectorAll('.agent-task-create-verify');
    for (var i = 0; i < boxes.length; i++) {
        var b = boxes[i];
        if (!b.checked) continue;
        var claim = b.value;
        var type = _agentTaskClaimToType[claim];
        if (!type) continue;
        var entry = { type: type, claim: claim };
        if (claim === 'tests_passed') {
            var cmd = (document.getElementById('agentTaskCreateTestsCommand').value || '').trim();
            if (!cmd) throw new Error('Command fuer tests_passed darf nicht leer sein.');
            entry.command = cmd;
        }
        entries.push(entry);
    }
    return entries;
}

function agentTaskCreateSubmit() {
    var title = (document.getElementById('agentTaskCreateTitle').value || '').trim();
    var errEl = document.getElementById('agentTaskCreateError');
    if (errEl) { errEl.style.display = 'none'; errEl.textContent = ''; }
    if (!title) {
        if (errEl) { errEl.textContent = 'Titel ist erforderlich.'; errEl.style.display = ''; }
        return;
    }
    var goal = (document.getElementById('agentTaskCreateGoal').value || '').trim();
    var allowedRaw = (document.getElementById('agentTaskCreateAllowed').value || '').trim();
    var projectRaw = (document.getElementById('agentTaskCreateProjectId').value || '').trim();
    var markerRaw = (document.getElementById('agentTaskCreateMarkerId').value || '').trim();

    var allowed = allowedRaw
        ? allowedRaw.split(/\r?\n/).map(function(s){return s.trim();}).filter(Boolean)
        : [];

    var verification;
    try {
        verification = _agentTaskCreateBuildVerification();
    } catch (e) {
        if (errEl) { errEl.textContent = e.message || String(e); errEl.style.display = ''; }
        return;
    }

    var payload = {
        title: title,
        goal: goal,
        allowed_files: allowed
    };
    if (verification.length) payload.required_verification = verification;
    if (projectRaw) {
        var pid = parseInt(projectRaw, 10);
        if (isNaN(pid)) {
            if (errEl) { errEl.textContent = 'project_id muss numerisch sein.'; errEl.style.display = ''; }
            return;
        }
        payload.project_id = pid;
    }
    if (markerRaw) payload.marker_id = markerRaw;

    var btn = document.getElementById('agentTaskCreateSubmitBtn');
    if (btn) btn.disabled = true;
    api.post('/api/agent-tasks', payload)
        .then(function(task) {
            closeModal('agentTaskCreateModal');
            if (typeof _showToast === 'function') {
                _showToast('Task #' + (task && task.task_id) + ' angelegt.');
            }
            if (typeof loadAgentTasks === 'function') loadAgentTasks();
        })
        .catch(function(err) {
            var msg = (err && err.body && err.body.error) || err.message || String(err);
            if (errEl) { errEl.textContent = 'Fehler: ' + msg; errEl.style.display = ''; }
        })
        .then(function() { if (btn) btn.disabled = false; });
}
