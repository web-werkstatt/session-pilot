/**
 * Cockpit Next-Action-Banner
 *
 * Kontextabhaengige "Was ist als Naechstes zu tun?"-Anzeige im Marker-Panel.
 * Leitet aus marker.gate_reason, marker.status, marker.execution_score und
 * workflow.current_step genau einen Schritt ab und rendert einen Primary-CTA.
 */
(function () {
    var TOTAL_STEPS = 7;

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

        // 4. Aktive Session
        if (status === 'in_progress') {
            return {
                step: 4,
                title: 'Session laeuft',
                description: 'Thread im Chat fortsetzen oder auf Ergebnis warten.',
                ctaLabel: 'Thread oeffnen',
                tab: 'chat'
            };
        }

        // 5. Write-back — Code fertig, Marker noch nicht auf done
        if (step === 'write_back' && status !== 'done') {
            return {
                step: 5,
                title: 'Ergebnis festschreiben',
                description: 'Session abgeschlossen. Marker auf done setzen und Commit vorbereiten.',
                ctaLabel: 'Abschluss vorbereiten',
                tab: 'output',
                focus: 'prompt'
            };
        }

        // 6. Rating fehlt nach done
        if (status === 'done' && ratingMissing) {
            return {
                step: 6,
                title: 'Bewertung nachholen',
                description: 'Score (0-5) und kurzen Kommentar zur Ausfuehrungsqualitaet hinterlassen.',
                ctaLabel: 'Bewerten',
                tab: 'history',
                focus: 'rating'
            };
        }

        // 7. Fertig
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

        var ctaAttrs = '';
        if (action.action === 'activate') {
            ctaAttrs = 'data-action="activate" data-marker-id="' + String(marker.marker_id).replace(/"/g, '&quot;') + '"';
        } else if (action.tab) {
            ctaAttrs = 'data-tab="' + action.tab + '"'
                + (action.focus ? ' data-focus="' + action.focus + '"' : '');
        }

        box.innerHTML = ''
            + '<div class="cna-step">Schritt ' + action.step + ' von ' + TOTAL_STEPS + '</div>'
            + '<div class="cna-title">' + escapeHtml(action.title) + '</div>'
            + '<div class="cna-desc">' + escapeHtml(action.description) + '</div>'
            + '<button type="button" class="ui-button ui-button--primary cna-cta" ' + ctaAttrs + '>'
            +   '<i data-lucide="arrow-right" class="icon icon-xs"></i> '
            +   escapeHtml(action.ctaLabel)
            + '</button>';
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
