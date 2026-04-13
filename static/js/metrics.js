/**
 * Review-Metriken Dashboard
 *
 * Laedt KPIs, Charts und Tabellen aus /api/review-metrics.
 * Nutzt api.get() (Fetch-Wrapper) und Chart.js fuer Visualisierung.
 */
(function () {
    'use strict';

    const statusEl = document.getElementById('metrics-status');
    let setupChart = null;
    let decisionsChart = null;

    // -----------------------------------------------------------------------
    // Init
    // -----------------------------------------------------------------------

    async function init() {
        document.getElementById('metrics-refresh-btn')
            ?.addEventListener('click', loadMetrics);
        await loadMetrics();
    }

    async function loadMetrics() {
        showStatus('Lade Metriken...', 'ok');
        try {
            const data = await api.get('/api/review-metrics');
            renderKPIs(data.kpis);
            renderSetupChart(data.setup_reviews);
            renderDecisionsChart(data.decisions);
            renderNoisiest(data.decisions.noisiest_findings);
            renderPolicyStats(data.policy_suggestions);
            renderCWOStats(data.cwo_reviews);
            clearStatus();
        } catch (err) {
            showStatus('Fehler beim Laden: ' + err.message, 'error');
        }
    }

    // -----------------------------------------------------------------------
    // KPI-Karten
    // -----------------------------------------------------------------------

    function renderKPIs(kpis) {
        const el = document.getElementById('metrics-kpis');
        if (!kpis) { el.innerHTML = '<div class="metrics-empty">Keine Daten</div>'; return; }

        const cards = [
            {
                label: 'Signal-Ratio',
                value: pct(kpis.signal_ratio),
                detail: `${kpis.total_shown} von ${kpis.total_generated} Findings nutzbar`,
                tone: kpis.signal_ratio >= 0.8 ? 'good' : kpis.signal_ratio >= 0.5 ? 'warn' : 'bad',
            },
            {
                label: 'Noise-Rate',
                value: pct(kpis.noise_rate),
                detail: `${kpis.total_filtered} gefiltert`,
                tone: kpis.noise_rate <= 0.1 ? 'good' : kpis.noise_rate <= 0.3 ? 'warn' : 'bad',
            },
            {
                label: 'Dismiss-Filter',
                value: pct(kpis.dismiss_filter_rate),
                detail: 'Bereits dismisste wiedergefunden',
                tone: 'neutral',
            },
            {
                label: 'Decision: Dismiss',
                value: pct(kpis.decision_dismiss_rate),
                detail: 'Anteil aller Entscheidungen',
                tone: kpis.decision_dismiss_rate > 0.5 ? 'warn' : 'neutral',
            },
            {
                label: 'Decision: Approve',
                value: pct(kpis.decision_approve_rate),
                detail: 'Anteil aller Entscheidungen',
                tone: kpis.decision_approve_rate > 0.3 ? 'good' : 'neutral',
            },
            {
                label: 'Policy Reject',
                value: pct(kpis.policy_reject_rate),
                detail: 'Abgelehnte Suggestions',
                tone: 'neutral',
            },
        ];

        el.innerHTML = cards.map(c => `
            <div class="kpi-card kpi-card--${c.tone}">
                <div class="kpi-card__label">${esc(c.label)}</div>
                <div class="kpi-card__value">${esc(c.value)}</div>
                <div class="kpi-card__detail">${esc(c.detail)}</div>
            </div>
        `).join('');
    }

    // -----------------------------------------------------------------------
    // Charts
    // -----------------------------------------------------------------------

    const CHART_COLORS = {
        shown: 'rgba(34, 197, 94, 0.8)',
        dismissed: 'rgba(239, 68, 68, 0.6)',
        lowConf: 'rgba(245, 158, 11, 0.6)',
    };

    function renderSetupChart(setup) {
        const canvas = document.getElementById('metrics-setup-chart');
        if (!canvas || !setup?.per_project?.length) return;

        const labels = setup.per_project.map(p => p.project_name);
        const shown = setup.per_project.map(p => p.shown);
        const dismissed = setup.per_project.map(p => p.filtered_dismissed);
        const lowConf = setup.per_project.map(p => p.filtered_low_conf);

        if (setupChart) setupChart.destroy();

        setupChart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [
                    { label: 'Angezeigt', data: shown, backgroundColor: CHART_COLORS.shown },
                    { label: 'Dismissed', data: dismissed, backgroundColor: CHART_COLORS.dismissed },
                    { label: 'Low Conf.', data: lowConf, backgroundColor: CHART_COLORS.lowConf },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#999', font: { size: 11 } } } },
                scales: {
                    x: { stacked: true, ticks: { color: '#999', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { stacked: true, beginAtZero: true, ticks: { color: '#999', stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                },
            },
        });
    }

    function renderDecisionsChart(decisions) {
        const canvas = document.getElementById('metrics-decisions-chart');
        if (!canvas || !decisions?.by_status) return;

        const statusColors = {
            pending: 'rgba(59, 130, 246, 0.7)',
            approved: 'rgba(34, 197, 94, 0.7)',
            dismissed: 'rgba(239, 68, 68, 0.7)',
            ignored_once: 'rgba(156, 163, 175, 0.5)',
        };

        const labels = Object.keys(decisions.by_status);
        const data = Object.values(decisions.by_status);
        const bgColors = labels.map(l => statusColors[l] || 'rgba(156,163,175,0.5)');

        if (decisionsChart) decisionsChart.destroy();

        decisionsChart = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels.map(capitalize),
                datasets: [{ data, backgroundColor: bgColors, borderWidth: 0 }],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'right', labels: { color: '#999', font: { size: 11 }, padding: 12 } },
                },
            },
        });
    }

    // -----------------------------------------------------------------------
    // Noisiest Findings Tabelle
    // -----------------------------------------------------------------------

    function renderNoisiest(findings) {
        const el = document.getElementById('metrics-noisiest');
        if (!findings?.length) {
            el.innerHTML = '<div class="metrics-empty">Keine Finding-Entscheidungen vorhanden</div>';
            return;
        }

        const rows = findings.map(f => `
            <tr>
                <td><span class="severity-badge severity-badge--${f.severity || 'info'}">${esc(f.severity || '?')}</span></td>
                <td>${esc(f.title || f.fingerprint)}</td>
                <td>${esc(f.review_type)}</td>
                <td>${f.project_count}</td>
                <td>${f.total_decisions}</td>
            </tr>
        `).join('');

        el.innerHTML = `
            <table class="metrics-table">
                <thead><tr>
                    <th>Severity</th><th>Finding</th><th>Reviewer</th>
                    <th>Projekte</th><th>Entscheidungen</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    }

    // -----------------------------------------------------------------------
    // Stats-Boxen
    // -----------------------------------------------------------------------

    function renderPolicyStats(policy) {
        const el = document.getElementById('metrics-policy-stats');
        if (!policy) { el.innerHTML = '<div class="metrics-empty">Keine Daten</div>'; return; }

        el.innerHTML = statItems([
            { value: policy.total, label: 'Gesamt' },
            { value: policy.by_status.pending || 0, label: 'Pending' },
            { value: policy.by_status.approved || 0, label: 'Approved' },
            { value: policy.by_status.rejected || 0, label: 'Rejected' },
            { value: pct(policy.reject_rate), label: 'Reject-Rate' },
        ]);
    }

    function renderCWOStats(cwo) {
        const el = document.getElementById('metrics-cwo-stats');
        if (!cwo) { el.innerHTML = '<div class="metrics-empty">Keine Daten</div>'; return; }

        el.innerHTML = statItems([
            { value: cwo.review_count, label: 'Reviews' },
            { value: cwo.total_generated, label: 'Generiert' },
            { value: cwo.total_shown, label: 'Angezeigt' },
            { value: cwo.total_filtered_low_conf, label: 'Low-Conf.' },
            { value: cwo.low_conf_warnings, label: 'Warnings' },
        ]);
    }

    function statItems(items) {
        return items.map(i => `
            <div class="stat-item">
                <div class="stat-item__value">${esc(String(i.value))}</div>
                <div class="stat-item__label">${esc(i.label)}</div>
            </div>
        `).join('');
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    function pct(ratio) {
        if (ratio == null || isNaN(ratio)) return '—';
        return (ratio * 100).toFixed(1) + '%';
    }

    function capitalize(s) {
        return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
    }

    function esc(s) {
        return typeof escapeHtml === 'function' ? escapeHtml(s) : String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function showStatus(msg, type) {
        statusEl.innerHTML = `<div class="status-msg status-msg--${type}">${esc(msg)}</div>`;
    }

    function clearStatus() {
        statusEl.innerHTML = '';
    }

    // -----------------------------------------------------------------------
    // Start
    // -----------------------------------------------------------------------

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
