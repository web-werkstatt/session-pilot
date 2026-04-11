(function() {
    // ADR-002 Stufe 1b: Policy-UI
    //
    // Vier Sektionen: Rollen, Tool-Profile, Aktive Policies, Pending Suggestions.
    // Zwei Aktionen: Seed-Defaults anlegen, Review anfordern.
    // Suggestions haben inline Approve/Reject.

    function setStatus(text, kind) {
        var el = document.getElementById('policies-status');
        if (!el) return;
        el.textContent = text || '';
        el.classList.remove('is-success', 'is-error');
        if (kind === 'success') el.classList.add('is-success');
        if (kind === 'error') el.classList.add('is-error');
    }

    function renderEmpty(hostId, text) {
        var host = document.getElementById(hostId);
        if (host) host.innerHTML = '<div class="policies-empty">' + escapeHtml(text) + '</div>';
    }

    // ---------- Rollen ----------

    async function loadRoles() {
        try {
            var data = await api.get('/api/policies/roles');
            renderRoles(data.roles || []);
        } catch (e) {
            renderEmpty('policies-roles', 'Fehler beim Laden: ' + (e.message || e));
        }
    }

    function renderRoles(roles) {
        var host = document.getElementById('policies-roles');
        if (!host) return;
        if (!roles.length) {
            host.innerHTML = '<div class="policies-empty">Keine Rollen angelegt. Klicke "Seed-Defaults anlegen".</div>';
            return;
        }
        host.innerHTML = roles.map(function(r) {
            return ''
                + '<div class="policies-item">'
                + '<div class="policies-item-id">' + escapeHtml(r.role_id) + '</div>'
                + '<div class="policies-item-title">' + escapeHtml(r.name || '') + '</div>'
                + (r.description ? '<div class="policies-item-desc">' + escapeHtml(r.description) + '</div>' : '')
                + '</div>';
        }).join('');
    }

    // ---------- Tool-Profile ----------

    async function loadToolProfiles() {
        try {
            var data = await api.get('/api/policies/tool-profiles');
            renderToolProfiles(data.tool_profiles || []);
        } catch (e) {
            renderEmpty('policies-tool-profiles', 'Fehler beim Laden: ' + (e.message || e));
        }
    }

    function renderToolProfiles(profiles) {
        var host = document.getElementById('policies-tool-profiles');
        if (!host) return;
        if (!profiles.length) {
            host.innerHTML = '<div class="policies-empty">Keine Tool-Profile angelegt.</div>';
            return;
        }
        host.innerHTML = profiles.map(function(p) {
            var meta = [p.cli, p.model, p.provider].filter(Boolean).map(escapeHtml).join(' · ');
            return ''
                + '<div class="policies-item">'
                + '<div class="policies-item-id">' + escapeHtml(p.tool_id) + '</div>'
                + '<div class="policies-item-meta">' + meta + '</div>'
                + (p.notes ? '<div class="policies-item-desc">' + escapeHtml(p.notes) + '</div>' : '')
                + '</div>';
        }).join('');
    }

    // ---------- Aktive Policies ----------

    async function loadAssignments() {
        try {
            var data = await api.get('/api/policies/assignments');
            renderAssignments(data.policies || []);
        } catch (e) {
            renderEmpty('policies-assignments', 'Fehler beim Laden: ' + (e.message || e));
        }
    }

    function renderAssignments(policies) {
        var host = document.getElementById('policies-assignments');
        if (!host) return;
        if (!policies.length) {
            host.innerHTML = '<div class="policies-empty">Keine aktiven Policies. Perplexity-Vorschlaege annehmen oder manuell setzen.</div>';
            return;
        }
        host.innerHTML = policies.map(function(p) {
            var meta = 'Rank ' + (p.rank || '?') + ' · Confidence ' + (p.confidence || '?') + ' · Source ' + escapeHtml(p.source || 'unknown');
            return ''
                + '<div class="policies-item">'
                + '<div class="policies-item-title">' + escapeHtml(p.role_id) + ' → ' + escapeHtml(p.tool_id) + '</div>'
                + '<div class="policies-item-meta">' + meta + (p.approved_by ? ' · approved by ' + escapeHtml(p.approved_by) : '') + '</div>'
                + (p.rationale ? '<div class="policies-item-desc">' + escapeHtml(p.rationale) + '</div>' : '')
                + '</div>';
        }).join('');
    }

    // ---------- Pending Suggestions ----------

    async function loadSuggestions() {
        try {
            var data = await api.get('/api/policies/suggestions');
            renderSuggestions(data.suggestions || []);
        } catch (e) {
            renderEmpty('policies-suggestions', 'Fehler beim Laden: ' + (e.message || e));
        }
    }

    function renderSuggestions(suggestions) {
        var host = document.getElementById('policies-suggestions');
        if (!host) return;
        if (!suggestions.length) {
            host.innerHTML = '<div class="policies-empty">Keine pending Suggestions. Klicke "Review anfordern".</div>';
            return;
        }
        host.innerHTML = suggestions.map(function(s) {
            var payload = s.payload || {};
            var payloadText = '';
            if (payload.role_id && payload.tool_id) {
                payloadText = escapeHtml(payload.role_id) + ' → ' + escapeHtml(payload.tool_id)
                    + (payload.rank ? ' · rank ' + payload.rank : '')
                    + (payload.confidence ? ' · confidence ' + payload.confidence : '');
            } else {
                payloadText = escapeHtml(JSON.stringify(payload));
            }
            return ''
                + '<div class="policies-suggestion" data-sid="' + s.suggestion_id + '">'
                + '<div class="policies-suggestion-head">'
                + '<span class="policies-suggestion-type">' + escapeHtml(s.suggestion_type || 'unknown') + '</span>'
                + '<span style="color:rgba(148,163,184,0.6);font-size:11px">#' + s.suggestion_id + '</span>'
                + '</div>'
                + '<div class="policies-suggestion-payload">' + payloadText + '</div>'
                + (s.rationale ? '<div class="policies-suggestion-rationale">' + escapeHtml(s.rationale) + '</div>' : '')
                + '<div class="policies-suggestion-actions">'
                + '<button class="btn-approve" data-action="approve" data-sid="' + s.suggestion_id + '">Annehmen</button>'
                + '<button class="btn-reject" data-action="reject" data-sid="' + s.suggestion_id + '">Ablehnen</button>'
                + '</div>'
                + '</div>';
        }).join('');

        host.querySelectorAll('[data-action="approve"]').forEach(function(btn) {
            btn.addEventListener('click', function() { approveSuggestion(btn.dataset.sid); });
        });
        host.querySelectorAll('[data-action="reject"]').forEach(function(btn) {
            btn.addEventListener('click', function() { rejectSuggestion(btn.dataset.sid); });
        });
    }

    // ---------- Aktionen ----------

    async function approveSuggestion(sid) {
        if (!confirm('Suggestion #' + sid + ' annehmen und als aktive Policy setzen?')) return;
        try {
            var data = await api.post('/api/policies/suggestions/' + encodeURIComponent(sid) + '/approve', {});
            setStatus('Suggestion ' + sid + ' angenommen (Policy #' + (data.applied_policy_id || '?') + ')', 'success');
            loadAssignments();
            loadSuggestions();
        } catch (e) {
            setStatus('Annahme fehlgeschlagen: ' + (e.message || e), 'error');
        }
    }

    async function rejectSuggestion(sid) {
        var reason = prompt('Grund fuer Ablehnung (optional):') || '';
        try {
            await api.post('/api/policies/suggestions/' + encodeURIComponent(sid) + '/reject', {reason: reason});
            setStatus('Suggestion ' + sid + ' abgelehnt', 'success');
            loadSuggestions();
        } catch (e) {
            setStatus('Ablehnung fehlgeschlagen: ' + (e.message || e), 'error');
        }
    }

    async function triggerReview() {
        setStatus('Review laeuft (Perplexity)...', null);
        var btn = document.getElementById('policies-review-btn');
        if (btn) btn.disabled = true;
        try {
            var data = await api.post('/api/policies/review', {});
            if (data.error) {
                setStatus('Review-Fehler: ' + data.error, 'error');
            } else {
                var count = (data.suggestions || []).length;
                setStatus('Review abgeschlossen. ' + count + ' neue Suggestion(s).', 'success');
            }
            loadSuggestions();
        } catch (e) {
            setStatus('Review fehlgeschlagen: ' + (e.message || e), 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    async function triggerSeed() {
        if (!confirm('Seed-Defaults anlegen? Bestehende Eintraege werden nicht ueberschrieben.')) return;
        var btn = document.getElementById('policies-seed-btn');
        if (btn) btn.disabled = true;
        try {
            var data = await api.post('/api/policies/seed-defaults', {});
            setStatus('Seed: ' + (data.roles_created || 0) + ' Rollen, ' + (data.tool_profiles_created || 0) + ' Tool-Profile angelegt.', 'success');
            loadRoles();
            loadToolProfiles();
        } catch (e) {
            setStatus('Seed fehlgeschlagen: ' + (e.message || e), 'error');
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    // ---------- Init ----------

    function init() {
        loadRoles();
        loadToolProfiles();
        loadAssignments();
        loadSuggestions();

        var seedBtn = document.getElementById('policies-seed-btn');
        if (seedBtn) seedBtn.addEventListener('click', triggerSeed);

        var reviewBtn = document.getElementById('policies-review-btn');
        if (reviewBtn) reviewBtn.addEventListener('click', triggerReview);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
