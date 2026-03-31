/**
 * Session Filters (Sprint 9) - AI-Scope, Outcome-Reason, Severity, Drill-down
 * Modulare Erweiterung fuer sessions2.js
 */

const SessionFilters = (function() {
    let outcomeReasons = {};
    let severityLevels = [];
    let currentScope = 'all';
    let currentOutcome = '';

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
            _buildOutcomeDropdown(filters.outcomes || {});
            _buildScopeButtons(filters.scope || {});
            applyUrlParams();
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

        const wrap = document.createElement('div');
        wrap.id = 'scopeFilter';
        wrap.className = 'scope-filter';

        const btns = [
            {value: 'all', label: 'All', count: scope.total || 0},
            {value: 'writes', label: 'Writes', count: scope.with_writes || 0},
            {value: 'tools', label: 'Tools', count: scope.with_tools || 0},
            {value: 'readonly', label: 'Read-only', count: scope.read_only || 0},
        ];
        btns.forEach(b => {
            const btn = document.createElement('button');
            btn.className = 'scope-btn' + (b.value === currentScope ? ' active' : '');
            btn.textContent = `${b.label} (${b.count})`;
            btn.dataset.scope = b.value;
            btn.onclick = function() {
                wrap.querySelectorAll('.scope-btn').forEach(s => s.classList.remove('active'));
                this.classList.add('active');
                currentScope = b.value;
                _pushFilterState();
                resetAndLoad();
            };
            wrap.appendChild(btn);
        });

        // Nach dem Outcome-Dropdown oder am Ende
        const pills = bar.querySelector('.filter-pills');
        if (pills) bar.insertBefore(wrap, pills);
        else bar.appendChild(wrap);
    }

    /**
     * Gibt aktive Filter-Parameter zurueck (fuer loadSessions)
     */
    function getFilterParams() {
        const params = {};
        if (currentOutcome) {
            params.outcome = currentOutcome;
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
        if (params.has('scope')) {
            currentScope = params.get('scope');
            const wrap = document.getElementById('scopeFilter');
            if (wrap) {
                wrap.querySelectorAll('.scope-btn').forEach(b => {
                    b.classList.toggle('active', b.dataset.scope === currentScope);
                });
            }
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
    };
})();
