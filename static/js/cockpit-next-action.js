/**
 * Cockpit Next-Action-Banner
 *
 * Kontextabhaengige "Was ist als Naechstes zu tun?"-Anzeige im Marker-Panel.
 * Leitet aus marker.gate_reason, marker.status, marker.execution_score und
 * workflow.current_step genau einen Schritt ab und rendert einen Primary-CTA.
 */
(function () {
    var TOTAL_STEPS = 5;

    function _deriveNextAction(marker, workflow) {
        if (!marker || !marker.marker_id) return null;

        var gateReason = String(marker.gate_reason || '').toLowerCase();
        var status = String(marker.status || 'todo').toLowerCase();
        var ratingMissing = marker.execution_score === null
            || marker.execution_score === undefined
            || marker.execution_score === '';
        var step = workflow && workflow.current_step;

        // 1. Prompt leer — Gate blockiert
        if (gateReason.indexOf('prompt') !== -1) {
            return {
                step: 1,
                title: 'Prompt formulieren',
                description: 'Der Marker braucht eine klare Anweisung fuer Claude Code, bevor er aktiviert werden kann.',
                ctaLabel: 'Prompt bearbeiten',
                tab: 'output',
                focus: 'prompt'
            };
        }

        // 2. Keine Checks — Gate blockiert
        if (gateReason.indexOf('check') !== -1) {
            return {
                step: 2,
                title: 'Abnahme-Checks definieren',
                description: 'Mindestens ein Check (Definition of Done) fehlt. Checks im Prompt-Abschnitt ergaenzen.',
                ctaLabel: 'Prompt bearbeiten',
                tab: 'output',
                focus: 'prompt'
            };
        }

        // 3. Aktivierbar, aber noch nicht gestartet
        if (marker.is_activatable && status === 'todo') {
            return {
                step: 3,
                title: 'Marker aktivieren',
                description: 'Prompt und Checks sind bereit. Kontext fuer Claude Code schreiben und Session starten.',
                ctaLabel: 'Aktivieren',
                action: 'activate'
            };
        }

        // 4. Aktive Session — CTA: abschliessen mit Rating (kombiniert)
        if (status === 'in_progress' || step === 'write_back') {
            return {
                step: 4,
                title: 'Session laeuft',
                description: 'Thread fortsetzen oder wenn Arbeit fertig: Marker abschliessen und bewerten.',
                ctaLabel: 'Thread oeffnen',
                tab: 'chat',
                secondary: {
                    label: 'Abschliessen + bewerten',
                    action: 'close_with_rating'
                }
            };
        }

        // 5. Abschluss + Bewertung in einem Schritt
        //    (alter Schritt 6 "Bewertung nachholen" entfaellt — retrospektives
        //    Rating ist wertlos, siehe RATING_PENDING_WINDOW.)
        //    Nur triggern wenn:
        //    - < 48h auf done (sonst Erinnerung weg)
        //    - last_session vorhanden (sonst gab es nichts zu bewerten)
        if (status === 'done' && ratingMissing) {
            // An den Done-Zeitpunkt koppeln (done_since aus
            // marker_workflow_states.completed_at), nicht an updated_at —
            // sonst verlaengert jede Feldaenderung das 48h-Fenster.
            var doneRef = marker.done_since || marker.updated_at;
            var doneAt = doneRef ? new Date(doneRef) : null;
            var ageHours = doneAt ? (Date.now() - doneAt.getTime()) / 3600000 : 0;
            var hasSession = !!(marker.last_session && String(marker.last_session).trim());
            if (!doneAt || ageHours > 48 || !hasSession) {
                return null;
            }
            return {
                step: 5,
                title: 'Bewertung nachholen',
                description: 'Der Marker ist abgeschlossen, aber noch nicht bewertet. Bewertung jetzt, solange die Erinnerung frisch ist.',
                ctaLabel: 'Jetzt bewerten',
                action: 'close_with_rating'
            };
        }

        // Fertig
        return null;
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
            + '<div class="cna-step">Schritt ' + action.step + ' von ' + TOTAL_STEPS + '</div>'
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
        if (tab && typeof switchPanelTab === 'function') {
            switchPanelTab(tab);
            if (focus) {
                // Fokus-Ziel pro Tab
                setTimeout(function () { _focusField(tab, focus); }, 50);
            }
        }
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
