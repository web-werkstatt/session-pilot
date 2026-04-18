/**
 * Agent Handoff Modal - Sprint Executor-Handoff Commit 3 (2026-04-18)
 * Entry point: openAgentHandoffModal(markerId, markerTitle, markerGoal)
 * Abhaengigkeiten: openModal/closeModal + _showToast (base.js), api.* (api.js)
 */

var _agentHandoffMarkerId = null;
var _agentHandoffTaskId = null;

function _agentHandoffCleanTitle(title) {
    if (!title) return '';
    // Trailing Marker-Tags entfernen: #sprint-..., #spec-..., #task-..., #ac-..., #doc-...
    return String(title).replace(/\s+#(sprint|spec|task|ac|doc|section)-[a-z0-9_\-]+$/i, '').trim();
}

function _agentHandoffTruncate(str, max) {
    str = String(str || '');
    if (str.length <= max) return str;
    return str.substring(0, max - 1) + '\u2026';
}

function openAgentHandoffModal(markerId, markerTitle, markerGoal) {
    var cleanTitle = _agentHandoffCleanTitle(markerTitle);
    _agentHandoffMarkerId = markerId;
    _agentHandoffTaskId = null;

    // Modal-Header + Marker-Kontext
    document.getElementById('agentHandoffTitle').textContent = 'Agent-Task anlegen';
    document.getElementById('agentHandoffMarkerTitle').textContent =
        cleanTitle + '  \u00B7  #' + markerId;

    // Create-Form vorausfuellen
    document.getElementById('agentHandoffNewTitle').value = cleanTitle || '';
    document.getElementById('agentHandoffNewGoal').value = markerGoal || '';
    document.getElementById('agentHandoffNewAllowed').value = '';

    _agentHandoffShowView('create');
    openModal('agentHandoffModal');

    // Existierenden offenen Task suchen. markerId einfangen, damit spaete
    // Responses nach Modal-Wechsel nicht in die neue Instanz hineinfunken.
    var requestedMarker = markerId;
    api.get('/api/agent-tasks?marker_id=' + encodeURIComponent(markerId))
        .then(function(task) {
            if (_agentHandoffMarkerId !== requestedMarker) return;
            if (task && task.task_id) {
                _agentHandoffShowTask(task);
            }
        })
        .catch(function(err) {
            if (_agentHandoffMarkerId !== requestedMarker) return;
            if (!err || err.status !== 404) {
                console.warn('agent-handoff: lookup failed', err);
            }
        });
}

function _agentHandoffShowView(view) {
    document.getElementById('agentHandoffCreateView').style.display = view === 'create' ? '' : 'none';
    document.getElementById('agentHandoffTaskView').style.display   = view === 'task'   ? '' : 'none';
    document.getElementById('agentHandoffLinkView').style.display   = view === 'link'   ? '' : 'none';
}

function _agentHandoffShowTask(task) {
    _agentHandoffTaskId = task.task_id;
    var cleanTitle = _agentHandoffCleanTitle(task.title);

    document.getElementById('agentHandoffTitle').textContent = 'Agent-Task #' + task.task_id;
    document.getElementById('agentHandoffTaskTitle').textContent = _agentHandoffTruncate(cleanTitle, 100);
    document.getElementById('agentHandoffTaskGoal').textContent = task.goal || '\u2014';

    var allowed = task.allowed_files || [];
    var allowedEl = document.getElementById('agentHandoffTaskAllowed');
    allowedEl.textContent = allowed.length ? allowed.join(', ') : 'keine (reiner Read-Task)';

    // State-Badge
    var stateEl = document.getElementById('agentHandoffTaskState');
    stateEl.textContent = 'offen';
    stateEl.style.background = 'var(--info-bg, #2a3d56)';
    stateEl.style.color = 'var(--text-heading, #fff)';

    // CLI-Command
    document.getElementById('agentHandoffCliCmd').textContent = 'claude-task finish ' + task.task_id;

    // Manuelle Felder zuruecksetzen
    document.getElementById('agentHandoffChangedFiles').value = '';
    document.getElementById('agentHandoffSummary').value = '';
    document.getElementById('agentHandoffDiffStat').value = '';
    document.getElementById('agentHandoffCopyHint').style.display = 'none';
    document.getElementById('agentHandoffResultError').style.display = 'none';

    // Verify-Block initial verbergen; _agentHandoffRefreshVerifyBlock() blendet
    // ihn ein, sobald ein execution_result vorhanden ist.
    var verifyBlock = document.getElementById('agentHandoffVerifyBlock');
    if (verifyBlock) verifyBlock.style.display = 'none';
    var verifyResult = document.getElementById('agentHandoffVerifyResult');
    if (verifyResult) { verifyResult.style.display = 'none'; verifyResult.innerHTML = ''; }
    var closeError = document.getElementById('agentHandoffCloseError');
    if (closeError) closeError.style.display = 'none';
    var closeBtn = document.getElementById('agentHandoffCloseBtn');
    if (closeBtn) closeBtn.disabled = true;

    _agentHandoffShowView('task');
    _agentHandoffRefreshVerifyBlock();
}

function _agentHandoffRefreshVerifyBlock() {
    // Sprint Workflow-Finalization Session 1: Verify-Block nur sichtbar, wenn
    // zu diesem Task bereits ein execution_result existiert. Danach letzten
    // Verify-Status laden, um Close-Button aktiv/inaktiv zu setzen.
    // Session L2 (Soll-Workflow-Luecken): Execution-Form/Readonly-Toggle
    // wird im gleichen Fetch-Durchgang aktualisiert.
    if (!_agentHandoffTaskId) return;
    var taskId = _agentHandoffTaskId;
    var block = document.getElementById('agentHandoffVerifyBlock');
    if (!block) return;
    api.get('/api/agent-tasks/' + taskId + '/execution')
        .then(function(execution) {
            if (_agentHandoffTaskId !== taskId) return;
            _agentHandoffRenderExecutionReadonly(execution);
            block.style.display = '';
            return api.get('/api/agent-tasks/' + taskId + '/verify')
                .then(function(v) {
                    if (_agentHandoffTaskId !== taskId) return;
                    _agentHandoffRenderVerify(v);
                })
                .catch(function(err) {
                    if (err && err.status === 404) return; // noch nie ausgefuehrt
                    throw err;
                });
        })
        .catch(function(err) {
            if (err && err.status === 404) {
                _agentHandoffShowExecutionForm();
                block.style.display = 'none';
                return;
            }
            console.warn('agent-handoff: verify block refresh failed', err);
        });
}

function _agentHandoffShowExecutionForm() {
    var form = document.getElementById('agentHandoffExecutionForm');
    var ro = document.getElementById('agentHandoffExecutionReadonly');
    if (form) form.style.display = '';
    if (ro) ro.style.display = 'none';
}

function _agentHandoffRenderExecutionReadonly(execution) {
    var form = document.getElementById('agentHandoffExecutionForm');
    var ro = document.getElementById('agentHandoffExecutionReadonly');
    if (!ro) return;
    if (form) form.style.display = 'none';
    ro.style.display = '';

    var files = (execution && execution.changed_files) || [];
    var filesEl = document.getElementById('agentHandoffExecFiles');
    if (filesEl) {
        filesEl.textContent = files.length ? files.join(', ') : '\u2014';
    }
    var agentEl = document.getElementById('agentHandoffExecAgent');
    if (agentEl) agentEl.textContent = (execution && execution.agent) || '\u2014';

    var summary = execution && execution.summary;
    var summaryWrap = document.getElementById('agentHandoffExecSummaryWrap');
    var summaryEl = document.getElementById('agentHandoffExecSummary');
    if (summary && summaryWrap && summaryEl) {
        summaryEl.textContent = summary;
        summaryWrap.style.display = '';
    } else if (summaryWrap) {
        summaryWrap.style.display = 'none';
    }

    var diff = execution && execution.diff_stat_text;
    var diffWrap = document.getElementById('agentHandoffExecDiffStatWrap');
    var diffEl = document.getElementById('agentHandoffExecDiffStat');
    if (diff && diffWrap && diffEl) {
        diffEl.textContent = diff;
        diffWrap.style.display = '';
    } else if (diffWrap) {
        diffWrap.style.display = 'none';
    }

    var oos = (execution && execution.out_of_scope_files) || [];
    var oosWrap = document.getElementById('agentHandoffExecOutOfScopeWrap');
    var oosEl = document.getElementById('agentHandoffExecOutOfScope');
    if (oos.length && oosWrap && oosEl) {
        oosEl.textContent = oos.join(', ');
        oosWrap.style.display = '';
    } else if (oosWrap) {
        oosWrap.style.display = 'none';
    }
}

function _agentHandoffRenderVerify(v) {
    var el = document.getElementById('agentHandoffVerifyResult');
    var closeBtn = document.getElementById('agentHandoffCloseBtn');
    if (!el) return;
    if (!v) {
        el.style.display = 'none';
        el.innerHTML = '';
        if (closeBtn) closeBtn.disabled = true;
        return;
    }
    var status = String(v.status || '').toLowerCase();
    var color;
    if (status === 'pass') color = 'var(--success, #3a9a4a)';
    else if (status === 'fail') color = 'var(--status-error, #d84a4a)';
    else color = 'var(--text-warning, #d89a4a)';

    var parts = ['<div><span style="font-weight:600;">Verify:</span> ' +
        '<span style="color:' + color + ';font-weight:600;text-transform:uppercase;">' +
        escapeHtml(status || 'unknown') + '</span></div>'];

    var unverified = v.unverified_claims || [];
    if (unverified.length) {
        parts.push('<div style="margin-top:4px;"><span style="color:var(--text-faint);">Offene Claims:</span> ' +
            unverified.map(escapeHtml).join(', ') + '</div>');
    }
    var checks = v.checks || [];
    if (checks.length) {
        var rows = checks.map(function(c) {
            var t = escapeHtml(c.claim || c.type || '');
            var s = escapeHtml(String(c.status || ''));
            var d = c.details ? ' &mdash; ' + escapeHtml(String(c.details)) : '';
            return '<div style="margin-left:10px;">&bull; ' + t + ': <em>' + s + '</em>' + d + '</div>';
        });
        parts.push('<div style="margin-top:4px;">' + rows.join('') + '</div>');
    }
    el.innerHTML = parts.join('');
    el.style.display = '';
    if (closeBtn) closeBtn.disabled = (status !== 'pass');
}

function agentHandoffRunVerify() {
    if (!_agentHandoffTaskId) return;
    var btn = document.getElementById('agentHandoffVerifyBtn');
    if (btn) btn.disabled = true;
    var errEl = document.getElementById('agentHandoffCloseError');
    if (errEl) errEl.style.display = 'none';
    api.post('/api/agent-tasks/' + _agentHandoffTaskId + '/verify', {})
        .then(function(v) { _agentHandoffRenderVerify(v); })
        .catch(function(err) {
            var el = document.getElementById('agentHandoffVerifyResult');
            if (el) {
                el.innerHTML = '<span style="color:var(--status-error);">Verify-Fehler: ' +
                    escapeHtml(err.message || String(err)) + '</span>';
                el.style.display = '';
            }
        })
        .then(function() { if (btn) btn.disabled = false; });
}

function agentHandoffDoClose() {
    if (!_agentHandoffTaskId) return;
    var errEl = document.getElementById('agentHandoffCloseError');
    var btn = document.getElementById('agentHandoffCloseBtn');
    if (errEl) errEl.style.display = 'none';
    if (btn) btn.disabled = true;
    api.post('/api/agent-tasks/' + _agentHandoffTaskId + '/close', {})
        .then(function(res) {
            var decision = (res && res.decision) || {};
            if (decision.can_close) {
                _showToast('Task geschlossen.');
                closeModal('agentHandoffModal');
            } else {
                if (errEl) {
                    errEl.textContent = 'Kann nicht schliessen: ' + (decision.reason || 'unbekannter Grund');
                    errEl.style.display = '';
                }
                if (btn) btn.disabled = false;
            }
        })
        .catch(function(err) {
            var body = err && err.body;
            var reason;
            if (body && body.decision && body.decision.reason) {
                reason = body.decision.reason;
            } else if (body && body.error) {
                reason = body.error;
            } else {
                reason = err.message || String(err);
            }
            if (errEl) {
                errEl.textContent = 'Kann nicht schliessen: ' + reason;
                errEl.style.display = '';
            }
            if (btn) btn.disabled = false;
        });
}

function agentHandoffCreate() {
    var title = (document.getElementById('agentHandoffNewTitle').value || '').trim();
    var goal  = (document.getElementById('agentHandoffNewGoal').value  || '').trim();
    var allowedRaw = (document.getElementById('agentHandoffNewAllowed').value || '').trim();
    if (!title) {
        _showToast('Titel ist erforderlich.', true);
        return;
    }
    var allowed = allowedRaw
        ? allowedRaw.split(/\r?\n/).map(function(s){return s.trim();}).filter(Boolean)
        : [];
    api.post('/api/agent-tasks', {
        title: title,
        goal: goal,
        marker_id: _agentHandoffMarkerId,
        allowed_files: allowed,
    })
    .then(function(task) { _agentHandoffShowTask(task); })
    .catch(function(err) { _showToast('Fehler: ' + (err.message || err), true); });
}

function _agentHandoffCopyToClipboard(text) {
    // Moderne API bevorzugt (HTTPS / localhost)
    if (navigator.clipboard && window.isSecureContext) {
        return navigator.clipboard.writeText(text);
    }
    // Fallback fuer HTTP-LAN-Setups (execCommand ist deprecated, funktioniert aber ueberall)
    return new Promise(function(resolve, reject) {
        try {
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            ta.style.top = '0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            ta.setSelectionRange(0, text.length);
            var ok = document.execCommand('copy');
            document.body.removeChild(ta);
            if (ok) resolve();
            else reject(new Error('execCommand copy returned false'));
        } catch (e) { reject(e); }
    });
}

function agentHandoffCopyPrompt() {
    if (!_agentHandoffTaskId) return;
    // Resolver-Kontext mitgeben: reichert den Prompt mit Handoff-Tail + aktivem Marker an
    var url = '/api/agent-tasks/' + _agentHandoffTaskId + '/prompt';
    var qs = [];
    if (typeof COCKPIT_PROJECT !== 'undefined' && COCKPIT_PROJECT) {
        qs.push('project=' + encodeURIComponent(COCKPIT_PROJECT));
    }
    if (_agentHandoffMarkerId) {
        qs.push('marker=' + encodeURIComponent(_agentHandoffMarkerId));
    }
    if (qs.length) url += '?' + qs.join('&');
    api.request(url, { raw: true })
        .then(function(resp) { return resp.text(); })
        .then(function(text) { return _agentHandoffCopyToClipboard(text); })
        .then(function() {
            document.getElementById('agentHandoffCopyHint').style.display = '';
        })
        .catch(function(err) {
            _showToast('Kopieren fehlgeschlagen: ' + (err.message || err), true);
        });
}

function agentHandoffSubmitExecution() {
    if (!_agentHandoffTaskId) return;
    var changedRaw = (document.getElementById('agentHandoffChangedFiles').value || '').trim();
    var summary    = (document.getElementById('agentHandoffSummary').value || '').trim();
    var diffStat   = (document.getElementById('agentHandoffDiffStat').value || '').trim();
    var errEl      = document.getElementById('agentHandoffResultError');
    var submitBtn  = document.getElementById('agentHandoffExecutionSubmitBtn');

    var changedFiles = changedRaw
        ? changedRaw.split(/\r?\n/).map(function(s){return s.trim();}).filter(Boolean)
        : [];

    var payload = {
        agent: 'dashboard-ui',
        changed_files: changedFiles,
        summary: summary || null,
        diff_stat_text: diffStat || null,
    };

    if (errEl) errEl.style.display = 'none';
    if (submitBtn) submitBtn.disabled = true;
    api.post('/api/agent-tasks/' + _agentHandoffTaskId + '/execution', payload)
        .then(function() {
            _showToast('Execution-Result eingereicht.');
            // Sprint Soll-Workflow-Luecken Session L2: Form ausblenden,
            // Readonly einblenden, dann Verify-Block refreshen.
            _agentHandoffRefreshVerifyBlock();
        })
        .catch(function(err) {
            if (errEl) {
                var body = err && err.body;
                var code = body && body.code;
                var msg;
                if (code === 'execution_already_recorded') {
                    msg = 'Execution bereits gespeichert. Aktualisiere Ansicht.';
                    _agentHandoffRefreshVerifyBlock();
                } else {
                    msg = (body && body.error) || err.message || String(err);
                }
                errEl.textContent = 'Fehler: ' + msg;
                errEl.style.display = '';
            }
        })
        .then(function() { if (submitBtn) submitBtn.disabled = false; });
}

function agentHandoffLinkExisting() {
    _agentHandoffShowView('link');
}

function agentHandoffShowCreate() {
    document.getElementById('agentHandoffTitle').textContent = 'Agent-Task anlegen';
    _agentHandoffShowView('create');
}

function agentHandoffDoLink() {
    var idVal = parseInt((document.getElementById('agentHandoffLinkId').value || '').trim(), 10);
    if (!idVal) return;
    api.get('/api/agent-tasks/' + idVal)
        .then(function(task) { _agentHandoffShowTask(task); })
        .catch(function() { _showToast('Task nicht gefunden.', true); });
}

// Entry Point aus dem Marker-Panel (copilot-board-panel.js:_currentSection).
// Fallback, wenn der Workflow-Ring fuer das Projekt nicht konfiguriert ist.
function openAgentHandoffFromPanel() {
    if (typeof _currentSection === 'undefined' || !_currentSection) {
        _showToast('Kein Marker ausgewaehlt.', true);
        return;
    }
    openAgentHandoffModal(
        _currentSection.marker_id,
        _currentSection.titel || _currentSection.title || _currentSection.marker_id,
        _currentSection.goal || _currentSection.ziel || ''
    );
}
