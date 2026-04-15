/**
 * Cockpit Next-Action-Banner
 *
 * Kontextabhaengige "Was ist als Naechstes zu tun?"-Anzeige im Marker-Panel.
 * Leitet aus marker.gate_reason, marker.status, marker.execution_score und
 * workflow.current_step genau einen Schritt ab und rendert einen Primary-CTA.
 */
(function () {
    /* Single Source of Truth fuers Step-Modell: Backend liefert
       workflow.steps[] mit id, number, title, description, cta_label,
       optional tab/focus/action/secondary. Das Banner rendert den Step,
       der workflow.current_step entspricht — keine eigene Ableitung mehr. */

    function _deriveNextAction(marker, workflow) {
        if (!marker || !marker.marker_id || !workflow) return null;
        var steps = workflow.steps || [];
        var currentId = workflow.current_step;
        var currentStep = null;
        for (var i = 0; i < steps.length; i++) {
            if (steps[i].id === currentId) { currentStep = steps[i]; break; }
        }
        if (!currentStep) return null;

        // "close"-Step unterdruecken, wenn Rating nicht sinnvoll:
        // keine Session ODER done_since > 48h (Fenster weg) ODER skipped.
        if (currentStep.id === 'close') {
            var hasSession = !!(marker.last_session && String(marker.last_session).trim());
            var doneRef = marker.done_since || marker.updated_at;
            var doneAt = doneRef ? new Date(doneRef) : null;
            var ageHours = doneAt ? (Date.now() - doneAt.getTime()) / 3600000 : 0;
            if (!hasSession || !doneAt || ageHours > 48 || marker.rating_skipped) return null;
        }

        return {
            step: currentStep.number,
            total: steps.length,
            title: currentStep.title,
            description: currentStep.description,
            ctaLabel: currentStep.cta_label,
            tab: currentStep.tab,
            focus: currentStep.focus,
            action: currentStep.action,
            secondary: currentStep.secondary || null
        };
    }

    function renderCockpitNextAction(marker, workflow) {
        var box = document.getElementById('cockpitNextAction');
        if (!box) return;

        var action = _deriveNextAction(marker, workflow);
        if (!action) {
            box.style.display = 'none';
            box.innerHTML = '';
            return;
        }

        function _ctaAttrs(act) {
            var markerIdAttr = String(marker.marker_id).replace(/"/g, '&quot;');
            if (act.action === 'activate') {
                return 'data-action="activate" data-marker-id="' + markerIdAttr + '"';
            }
            if (act.action === 'close_with_rating') {
                return 'data-action="close_with_rating" data-marker-id="' + markerIdAttr + '"';
            }
            if (act.action === 'skip_rating') {
                return 'data-action="skip_rating" data-marker-id="' + markerIdAttr + '"';
            }
            if (act.tab) {
                return 'data-tab="' + act.tab + '"'
                    + (act.focus ? ' data-focus="' + act.focus + '"' : '');
            }
            return '';
        }

        var primaryHtml = '<button type="button" class="ui-button ui-button--primary cna-cta" ' + _ctaAttrs(action) + '>'
            + '<i data-lucide="arrow-right" class="icon icon-xs"></i> '
            + escapeHtml(action.ctaLabel)
            + '</button>';
        var secondaryHtml = '';
        if (action.secondary) {
            secondaryHtml = '<button type="button" class="ui-button ui-button--ghost cna-cta cna-cta--secondary" '
                + _ctaAttrs(action.secondary) + '>'
                + escapeHtml(action.secondary.label)
                + '</button>';
        }

        box.innerHTML = ''
            + '<div class="cna-step">Schritt ' + action.step + ' von ' + (action.total || 5) + '</div>'
            + '<div class="cna-title">' + escapeHtml(action.title) + '</div>'
            + '<div class="cna-desc">' + escapeHtml(action.description) + '</div>'
            + '<div class="cna-actions">' + primaryHtml + secondaryHtml + '</div>';
        box.style.display = '';
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function _handleCtaClick(btn) {
        var markerId = btn.getAttribute('data-marker-id');
        var actionName = btn.getAttribute('data-action');
        var tab = btn.getAttribute('data-tab');
        var focus = btn.getAttribute('data-focus');

        if (actionName === 'activate' && markerId && typeof activateMarker === 'function') {
            activateMarker(markerId);
            return;
        }
        if (actionName === 'close_with_rating' && markerId && typeof openCockpitCloseModal === 'function') {
            openCockpitCloseModal(markerId);
            return;
        }
        if (actionName === 'skip_rating' && markerId) {
            _skipRating(markerId);
            return;
        }
        if (tab && typeof switchPanelTab === 'function') {
            switchPanelTab(tab);
            if (focus) {
                // Fokus-Ziel pro Tab
                setTimeout(function () { _focusField(tab, focus); }, 50);
            }
        }
    }

    function _skipRating(markerId) {
        var payload = {};
        if (typeof _currentProjectId !== 'undefined' && _currentProjectId) payload.project_id = _currentProjectId;
        if (typeof PLAN_ID !== 'undefined' && PLAN_ID) payload.plan_id = PLAN_ID;
        api.post('/api/marker/' + encodeURIComponent(markerId) + '/rating-skip', payload)
            .then(function () {
                if (typeof _showToast === 'function') _showToast('Rating fuer diesen Marker ignoriert');
                var box = document.getElementById('cockpitNextAction');
                if (box) { box.style.display = 'none'; box.innerHTML = ''; }
                if (typeof _loadMarkerContext === 'function' && typeof _currentSection !== 'undefined'
                    && _currentSection && _currentSection.marker_id === markerId) {
                    _loadMarkerContext(markerId);
                }
                if (typeof loadCockpitWorkflow === 'function') loadCockpitWorkflow();
            })
            .catch(function (err) {
                var msg = (err && err.message) ? err.message : 'Fehler beim Ignorieren';
                if (typeof _showToast === 'function') _showToast(msg, true);
            });
    }

    function _focusField(tab, focus) {
        if (tab === 'output' && focus === 'prompt') {
            var ta = document.getElementById('panelMarkerPrompt');
            if (ta) {
                ta.readOnly = false;
                ta.focus();
                ta.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }
        if (tab === 'history' && focus === 'rating') {
            var sel = document.getElementById('panelExecutionScore');
            if (sel) {
                sel.focus();
                sel.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }
    }

    document.addEventListener('click', function (e) {
        var btn = e.target.closest && e.target.closest('.cna-cta');
        if (btn) _handleCtaClick(btn);
    });

    window.renderCockpitNextAction = renderCockpitNextAction;
})();
