/**
 * Session Filters (Sprint 9) - AI-Scope, Outcome-Reason, Severity, Drill-down
 * Modulare Erweiterung fuer sessions2.js
 */

const SessionFilters = (function() {
    let outcomeReasons = {};
    let severityLevels = [];
    let currentScope = 'all';
    let currentOutcome = '';
    let currentOutcomeReason = '';
    let projectDefaults = {};

    /**
     * Laedt Filter-Optionen vom Server und baut Dropdowns auf
     */
    async function init() {
        try {
            const [reasons, filters] = await Promise.all([
                api.get('/api/sessions/outcome-reasons'),
                api.get('/api/sessions/filters'),
            ]);
            outcomeReasons = reasons.reasons || {};
            severityLevels = reasons.severities || [];
            projectDefaults = filters.project_defaults || {};
            _buildOutcomeDropdown(filters.outcomes || {});
            _buildScopeButtons(filters.scope || {});
            _hookProjectChange();
            applyUrlParams();
            _applyProjectDefaults();
        } catch(e) {
            console.error('SessionFilters init error:', e);
        }
    }

    /**
     * Baut Outcome-Filter-Dropdown
     */
    function _buildOutcomeDropdown(outcomes) {
        const bar = document.querySelector('.filter-bar');
        if (!bar || document.getElementById('filterOutcome')) return;

        const sel = document.createElement('select');
        sel.id = 'filterOutcome';
        sel.className = 'filter-outcome';
        sel.onchange = function() {
            currentOutcome = this.value;
            _pushFilterState();
            resetAndLoad();
        };

        const opts = [
            {value: '', label: 'All Outcomes'},
            {value: 'ok', label: `OK (${outcomes.ok || 0})`},
            {value: 'needs_fix', label: `Needs Fix (${outcomes.needs_fix || 0})`},
            {value: 'reverted', label: `Reverted (${outcomes.reverted || 0})`},
            {value: 'partial', label: `Partial (${outcomes.partial || 0})`},
            {value: 'unrated', label: `Unrated (${outcomes.unrated || outcomes['null'] || 0})`},
        ];
        opts.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.value;
            opt.textContent = o.label;
            sel.appendChild(opt);
        });

        // Vor den Quick-Filter-Pills einfuegen
        const pills = bar.querySelector('.filter-pills');
        if (pills) bar.insertBefore(sel, pills);
        else bar.appendChild(sel);
    }

    /**
     * Baut AI-Scope Toggle-Buttons
     */
    function _buildScopeButtons(scope) {
        const bar = document.querySelector('.filter-bar');
        if (!bar || document.getElementById('scopeFilter')) return;

        // Checkbox: "Only AI-relevant"
        const cbWrap = document.createElement('label');
        cbWrap.className = 'scope-checkbox';
        cbWrap.innerHTML = `<input type="checkbox" id="scopeAiOnly" onchange="SessionFilters.toggleAiOnly(this.checked)"> <span>AI-relevant only</span>`;
        const pills = bar.querySelector('.filter-pills');
        if (pills) bar.insertBefore(cbWrap, pills);
        else bar.appendChild(cbWrap);

        // Scope-Dropdown
        const sel = document.createElement('select');
        sel.id = 'scopeFilter';
        sel.className = 'filter-outcome';
        sel.onchange = function() {
            currentScope = this.value;
            _pushFilterState();
            resetAndLoad();
        };
        const opts = [
            {value: 'all', label: 'All Sessions'},
            {value: 'writes', label: `Write Sessions (${scope.with_writes || 0})`},
            {value: 'tools', label: `Tool Calls (${scope.with_tools || 0})`},
            {value: 'readonly', label: `Read-only (${scope.read_only || 0})`},
        ];
        opts.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.value;
            opt.textContent = o.label;
            sel.appendChild(opt);
        });
        if (pills) bar.insertBefore(sel, pills);
        else bar.appendChild(sel);
    }

    function toggleAiOnly(checked) {
        currentScope = checked ? 'tools' : 'all';
        const sel = document.getElementById('scopeFilter');
        if (sel) sel.value = currentScope;
        _pushFilterState();
        resetAndLoad();
    }

    /**
     * Gibt aktive Filter-Parameter zurueck (fuer loadSessions)
     */
    function getFilterParams() {
        const params = {};
        if (currentOutcome) {
            params.outcome = currentOutcome;
        }
        if (currentOutcomeReason) {
            params.outcome_reason = currentOutcomeReason;
        }
        if (currentScope && currentScope !== 'all') {
            params.scope = currentScope;
        }
        return params;
    }

    /**
     * Erzeugt Severity-Badge HTML
     */
    function severityBadge(severity) {
        if (!severity) return '';
        return `<span class="severity-badge severity-${severity}">${severity}</span>`;
    }

    /**
     * Erzeugt Outcome-Reason Tag HTML
     */
    function reasonTag(reason) {
        if (!reason) return '';
        const label = reason.replace(/_/g, ' ');
        return `<span class="outcome-reason">${label}</span>`;
    }

    /**
     * Gibt Reason-Optionen fuer einen Outcome-Typ zurueck
     */
    function getReasonsForOutcome(outcome) {
        return outcomeReasons[outcome] || [];
    }

    /**
     * Gibt Severity-Levels zurueck
     */
    function getSeverities() {
        return severityLevels;
    }

    /**
     * Setzt reason + severity fuer eine Session
     */
    async function setOutcomeDetail(uuid, reason, severity) {
        return api.post(`/api/sessions/${uuid}/outcome-detail`, {reason, severity});
    }

    // --- Project Policy Defaults (9.7) ---

    /**
     * Wendet Default-Filter an wenn ein Projekt gewaehlt ist und keine URL-Parameter gesetzt sind
     */
    function _applyProjectDefaults() {
        // URL-Parameter haben Vorrang - wenn scope oder outcome in URL, keine Defaults
        const params = new URLSearchParams(window.location.search);
        if (params.has('scope') || params.has('outcome')) return;

        const project = document.getElementById('filterProject')?.value;
        if (!project || !projectDefaults[project]) return;

        const defaults = projectDefaults[project];
        if (defaults.scope && defaults.scope !== 'all') {
            currentScope = defaults.scope;
            const sel = document.getElementById('scopeFilter');
            if (sel) sel.value = currentScope;
        }
        if (defaults.ai_only) {
            const cb = document.getElementById('scopeAiOnly');
            if (cb) cb.checked = true;
            if (!currentScope || currentScope === 'all') currentScope = 'tools';
            const sel = document.getElementById('scopeFilter');
            if (sel) sel.value = currentScope;
        }
    }

    /**
     * Reagiert auf Projekt-Dropdown-Wechsel: Defaults neu anwenden
     */
    function _hookProjectChange() {
        const sel = document.getElementById('filterProject');
        if (!sel) return;
        sel.addEventListener('change', () => {
            // Reset scope to defaults of new project
            currentScope = 'all';
            currentOutcome = '';
            const scopeSel = document.getElementById('scopeFilter');
            if (scopeSel) scopeSel.value = 'all';
            const outcomeSel = document.getElementById('filterOutcome');
            if (outcomeSel) outcomeSel.value = '';
            const cb = document.getElementById('scopeAiOnly');
            if (cb) cb.checked = false;
            _applyProjectDefaults();
        });
    }

    // --- Drill-down / URL State ---

    /**
     * Liest Filter-State aus URL-Parametern
     */
    function applyUrlParams() {
        const params = new URLSearchParams(window.location.search);

        if (params.has('outcome')) {
            currentOutcome = params.get('outcome');
            const sel = document.getElementById('filterOutcome');
            if (sel) sel.value = currentOutcome;
        }
        if (params.has('outcome_reason')) {
            currentOutcomeReason = params.get('outcome_reason');
        }
        if (params.has('scope')) {
            currentScope = params.get('scope');
            const sel = document.getElementById('scopeFilter');
            if (sel) sel.value = currentScope;
            const cb = document.getElementById('scopeAiOnly');
            if (cb) cb.checked = (currentScope === 'tools');
        }
        if (params.has('account')) {
            const sel = document.getElementById('filterAccount');
            if (sel) sel.value = params.get('account');
        }
        if (params.has('project')) {
            const sel = document.getElementById('filterProject');
            if (sel) sel.value = params.get('project');
        }
        if (params.has('date_from')) {
            document.getElementById('filterDateFrom').value = params.get('date_from');
        }
        if (params.has('date_to')) {
            document.getElementById('filterDateTo').value = params.get('date_to');
        }
    }

    /**
     * Schreibt aktuellen Filter-State in URL (ohne Reload)
     */
    function _pushFilterState() {
        const params = new URLSearchParams();
        if (currentOutcome) params.set('outcome', currentOutcome);
        if (currentOutcomeReason) params.set('outcome_reason', currentOutcomeReason);
        if (currentScope && currentScope !== 'all') params.set('scope', currentScope);

        const account = document.getElementById('filterAccount')?.value;
        const project = document.getElementById('filterProject')?.value;
        const dateFrom = document.getElementById('filterDateFrom')?.value;
        const dateTo = document.getElementById('filterDateTo')?.value;
        if (account) params.set('account', account);
        if (project) params.set('project', project);
        if (dateFrom) params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);

        const qs = params.toString();
        const url = window.location.pathname + (qs ? '?' + qs : '');
        history.replaceState(null, '', url);
    }

    /**
     * Erzeugt Drill-down-Link URL
     */
    function drilldownUrl(filters) {
        const params = new URLSearchParams(filters);
        return '/sessions?' + params.toString();
    }

    return {
        init,
        getFilterParams,
        severityBadge,
        reasonTag,
        getReasonsForOutcome,
        getSeverities,
        setOutcomeDetail,
        applyUrlParams,
        drilldownUrl,
        toggleAiOnly,
    };
})();
