/**
 * Finding-Decisions: Approve/Dismiss/Ignore-Buttons fuer Review-Findings.
 *
 * Generisches UI-Modul das von setup-reviewer.js und context-window-optimizer.js
 * genutzt wird. Rendert Action-Buttons und Dismiss-Dialog mit Reason-Presets.
 *
 * Abhaengigkeiten: api.js (api.post), base.js (escapeHtml)
 */
(function() {
    'use strict';

    var DISMISS_REASONS = [
        {value: 'bewusst_so', label: 'Bewusst so'},
        {value: 'runtime_datei', label: 'Runtime-Datei'},
        {value: 'kein_projektziel', label: 'Kein Projektziel'},
        {value: 'dupliziert', label: 'Dupliziert'}
    ];

    /**
     * Rendert Action-Buttons fuer ein Finding (HTML-String).
     * @param {Object} f - Finding mit _fingerprint, _decision_status, _review_type
     * @param {string} projectName - Projektname fuer API-Calls
     * @returns {string} HTML
     */
    function renderActionButtons(f, projectName) {
        if (!f._fingerprint) return '';
        var status = f._decision_status || 'pending';

        if (status === 'dismissed') {
            return '<div class="fd-actions fd-dismissed">'
                + '<span class="fd-badge fd-badge--dismissed">Dismissed</span>'
                + '<button class="fd-btn fd-btn--reset" onclick="findingDecisions.reset(\''
                + escapeHtml(f._fingerprint) + '\',\'' + escapeHtml(f._review_type || 'setup')
                + '\',\'' + escapeHtml(projectName) + '\')">Wiederherstellen</button>'
                + '</div>';
        }
        if (status === 'approved') {
            return '<div class="fd-actions fd-approved">'
                + '<span class="fd-badge fd-badge--approved">Akzeptiert</span>'
                + '<button class="fd-btn fd-btn--reset" onclick="findingDecisions.reset(\''
                + escapeHtml(f._fingerprint) + '\',\'' + escapeHtml(f._review_type || 'setup')
                + '\',\'' + escapeHtml(projectName) + '\')">Wiederherstellen</button>'
                + '</div>';
        }

        // Status: pending — zeige Aktions-Buttons
        var snap = encodeURIComponent(JSON.stringify(_buildSnapshot(f)));
        return '<div class="fd-actions">'
            + '<button class="fd-btn fd-btn--approve" onclick="findingDecisions.decide(\''
            + escapeHtml(f._fingerprint) + '\',\'approved\',\'' + escapeHtml(f._review_type || 'setup')
            + '\',\'' + escapeHtml(projectName) + '\',' + "'" + snap + "'" + ')">Akzeptieren</button>'
            + '<button class="fd-btn fd-btn--dismiss" onclick="findingDecisions.showDismissDialog(\''
            + escapeHtml(f._fingerprint) + '\',\'' + escapeHtml(f._review_type || 'setup')
            + '\',\'' + escapeHtml(projectName) + '\',' + "'" + snap + "'" + ')">Dismiss</button>'
            + '<button class="fd-btn fd-btn--ignore" onclick="findingDecisions.decide(\''
            + escapeHtml(f._fingerprint) + '\',\'ignored_once\',\'' + escapeHtml(f._review_type || 'setup')
            + '\',\'' + escapeHtml(projectName) + '\',' + "'" + snap + "'" + ')">Einmal ignorieren</button>'
            + '</div>';
    }

    function _buildSnapshot(f) {
        var snap = {};
        var keys = ['area', 'check_id', 'severity', 'title', 'problem', 'detail',
                     'recommended_change', 'recommendation', 'why_it_matters', 'can_autofix'];
        keys.forEach(function(k) { if (f[k] !== undefined) snap[k] = f[k]; });
        return snap;
    }

    /**
     * API-Call: Entscheidung speichern.
     */
    function decide(fingerprint, status, reviewType, projectName, snapshotEncoded) {
        var snapshot = {};
        try { snapshot = JSON.parse(decodeURIComponent(snapshotEncoded)); } catch(e) {}

        api.post('/api/project/' + encodeURIComponent(projectName) + '/findings/decide', {
            fingerprint: fingerprint,
            review_type: reviewType,
            status: status,
            finding_snapshot: snapshot
        }).then(function() {
            _reloadCurrentView(projectName);
        }).catch(function(e) {
            alert('Fehler: ' + (e.message || e));
        });
    }

    /**
     * Dismiss-Dialog mit Reason-Presets.
     */
    function showDismissDialog(fingerprint, reviewType, projectName, snapshotEncoded) {
        var overlay = document.createElement('div');
        overlay.className = 'fd-overlay';
        overlay.innerHTML = ''
            + '<div class="fd-dialog">'
            + '<div class="fd-dialog-title">Finding dismissmen</div>'
            + '<div class="fd-dialog-label">Grund:</div>'
            + '<div class="fd-dialog-reasons">'
            + DISMISS_REASONS.map(function(r) {
                return '<button class="fd-reason-btn" data-reason="' + r.value + '">'
                    + escapeHtml(r.label) + '</button>';
            }).join('')
            + '</div>'
            + '<div class="fd-dialog-label" style="margin-top:8px">Notiz (optional):</div>'
            + '<input class="fd-dialog-input" type="text" placeholder="Freitext..." />'
            + '<div class="fd-dialog-actions">'
            + '<button class="fd-btn fd-btn--dismiss fd-dialog-confirm">Dismiss</button>'
            + '<button class="fd-btn fd-btn--reset fd-dialog-cancel">Abbrechen</button>'
            + '</div>'
            + '</div>';

        document.body.appendChild(overlay);

        var selectedReason = null;
        overlay.querySelectorAll('.fd-reason-btn').forEach(function(btn) {
            btn.addEventListener('click', function() {
                overlay.querySelectorAll('.fd-reason-btn').forEach(function(b) {
                    b.classList.remove('fd-reason-btn--selected');
                });
                btn.classList.add('fd-reason-btn--selected');
                selectedReason = btn.dataset.reason;
            });
        });

        overlay.querySelector('.fd-dialog-cancel').addEventListener('click', function() {
            document.body.removeChild(overlay);
        });

        overlay.querySelector('.fd-dialog-confirm').addEventListener('click', function() {
            var note = overlay.querySelector('.fd-dialog-input').value.trim();
            var snapshot = {};
            try { snapshot = JSON.parse(decodeURIComponent(snapshotEncoded)); } catch(e) {}

            api.post('/api/project/' + encodeURIComponent(projectName) + '/findings/decide', {
                fingerprint: fingerprint,
                review_type: reviewType,
                status: 'dismissed',
                dismiss_reason: selectedReason,
                dismiss_note: note || undefined,
                finding_snapshot: snapshot
            }).then(function() {
                document.body.removeChild(overlay);
                _reloadCurrentView(projectName);
            }).catch(function(e) {
                alert('Fehler: ' + (e.message || e));
            });
        });

        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) document.body.removeChild(overlay);
        });
    }

    /**
     * API-Call: Entscheidung zuruecksetzen.
     */
    function reset(fingerprint, reviewType, projectName) {
        api.post('/api/project/' + encodeURIComponent(projectName) + '/findings/reset', {
            fingerprint: fingerprint,
            review_type: reviewType
        }).then(function() {
            _reloadCurrentView(projectName);
        }).catch(function(e) {
            alert('Fehler: ' + (e.message || e));
        });
    }

    /**
     * Laedt die aktuelle Ansicht neu (Setup-Reviewer Banner oder CWO-Panel).
     */
    function _reloadCurrentView(projectName) {
        if (window.setupReviewer && window.setupReviewer.mountBanner) {
            window.setupReviewer.mountBanner(projectName);
        }
        if (window.cwo && window.cwo.mountPanel) {
            window.cwo.mountPanel(projectName);
        }
    }

    // Public API
    window.findingDecisions = {
        renderActionButtons: renderActionButtons,
        decide: decide,
        showDismissDialog: showDismissDialog,
        reset: reset
    };
})();
