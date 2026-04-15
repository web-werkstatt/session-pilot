/**
 * Sprint sprint-task-backfill (2026-04-15):
 * Fuzzy-Match-UI: bestehende Marker (task_id=NULL) an plan_tasks zuordnen.
 *
 * Arbeitet mit aktuellem PLAN_ID aus Cockpit-Kontext. Nutzt modal-System +
 * api.js (POST/GET-Wrapper) aus base.js.
 */
(function () {
    'use strict';

    const AUTO_APPLY_THRESHOLD = 0.9;
    let currentSuggestions = [];

    function currentPlanId() {
        return typeof PLAN_ID !== 'undefined' && PLAN_ID ? PLAN_ID : null;
    }

    function listEl() {
        return document.getElementById('taskBackfillList');
    }

    function setStatus(msg, isError) {
        const list = listEl();
        if (!list) return;
        list.innerHTML = `<div class="task-backfill-status-msg${isError ? ' is-error' : ''}">${msg}</div>`;
    }

    function setStats({ orphans, pending }) {
        const o = document.getElementById('tbfOrphansStat');
        const p = document.getElementById('tbfPendingStat');
        if (o) o.textContent = `${orphans ?? '–'} offen`;
        if (p) p.textContent = `${pending ?? '–'} Vorschl\u00e4ge`;
    }

    async function openTaskBackfillModal() {
        if (!currentPlanId()) {
            if (typeof showToast === 'function') showToast('Kein Plan im Kontext — Backfill nur in Plan-Ansicht verfuegbar.');
            return;
        }
        if (typeof openModal === 'function') openModal('taskBackfillModal');
        await refreshSuggestions();
    }

    async function refreshSuggestions() {
        const planId = currentPlanId();
        if (!planId) return;
        setStatus('Lade Vorschlaege...');
        try {
            const data = await api.get(`/api/plans/${planId}/task-matches?status=pending`);
            currentSuggestions = data.suggestions || [];
            setStats({ orphans: data.orphans_remaining, pending: currentSuggestions.length });
            renderSuggestions(currentSuggestions);
        } catch (err) {
            setStatus(`Fehler beim Laden: ${err.message || err}`, true);
        }
    }

    async function taskBackfillRecompute() {
        const planId = currentPlanId();
        if (!planId) return;
        setStatus('Berechne Matches...');
        try {
            const stats = await api.post(`/api/plans/${planId}/task-matches/recompute`, {});
            const parts = [
                `${stats.created} neu`,
                `${stats.skipped_existing} vorhanden`,
                `${stats.skipped_low_score} zu schwach`,
            ];
            if (typeof showToast === 'function') showToast(`Matches: ${parts.join(', ')}`);
            await refreshSuggestions();
        } catch (err) {
            setStatus(`Fehler: ${err.message || err}`, true);
        }
    }

    async function taskBackfillAutoApply() {
        const planId = currentPlanId();
        if (!planId) return;
        const btn = document.getElementById('tbfAutoApplyBtn');
        if (btn) btn.disabled = true;
        try {
            const result = await api.post(`/api/plans/${planId}/task-matches/auto-apply`, {
                min_score: AUTO_APPLY_THRESHOLD,
            });
            if (typeof showToast === 'function') showToast(`${result.applied}/${result.candidates} angewendet, ${result.orphans_remaining} Orphans verbleiben.`);
            await refreshSuggestions();
        } catch (err) {
            setStatus(`Fehler: ${err.message || err}`, true);
        } finally {
            if (btn) btn.disabled = false;
        }
    }

    function renderSuggestions(items) {
        const list = listEl();
        if (!list) return;
        if (!items.length) {
            list.innerHTML = '<div class="task-backfill-empty">Keine pending Vorschlaege. Klicke <strong>Neu berechnen</strong> um aktuelle Orphans zu matchen.</div>';
            return;
        }
        list.innerHTML = items.map(renderItem).join('');
        if (window.lucide && typeof lucide.createIcons === 'function') lucide.createIcons();
    }

    function renderItem(s) {
        const score = Number(s.score || 0);
        const pct = Math.round(score * 100);
        const autoClass = s.auto_apply_hint ? ' is-auto' : '';
        const markerTitle = window.escapeHtml(s.marker?.titel || '(kein Titel)');
        const taskTitle = window.escapeHtml(s.task?.title || '(kein Titel)');
        const ctx = [s.task?.section_key, s.task?.spec_key].filter(Boolean).map(escapeHtml).join(' / ');
        return `
            <div class="task-backfill-item${autoClass}" data-id="${s.id}">
                <div class="task-backfill-item-info">
                    <div class="task-backfill-marker-title" title="${markerTitle}">${markerTitle}</div>
                    <div class="task-backfill-arrow">&darr; wird zugeordnet zu</div>
                    <div class="task-backfill-task-title" title="${taskTitle}">${taskTitle}</div>
                    <div class="task-backfill-task-context">${ctx || '&nbsp;'}</div>
                </div>
                <div class="task-backfill-score">
                    <div class="task-backfill-score-value">${score.toFixed(2)}</div>
                    <div class="task-backfill-score-bar"><div class="task-backfill-score-bar-fill" style="width:${pct}%"></div></div>
                    <div class="task-backfill-score-method">${window.escapeHtml(s.method || '')}</div>
                </div>
                <div class="task-backfill-controls">
                    <button class="ui-button ui-button--primary" onclick="taskBackfillApprove(${s.id})" title="Zuordnung anwenden">
                        <i data-lucide="check" class="icon icon-xs"></i>
                    </button>
                    <button class="ui-button ui-button--ghost" onclick="taskBackfillReject(${s.id})" title="Vorschlag verwerfen">
                        <i data-lucide="x" class="icon icon-xs"></i>
                    </button>
                </div>
            </div>
        `;
    }

    async function taskBackfillApprove(id) {
        try {
            await api.post(`/api/task-matches/${id}/approve`, {});
            await refreshSuggestions();
        } catch (err) {
            if (typeof showToast === 'function') showToast(`Fehler: ${err.message || err}`);
        }
    }

    async function taskBackfillReject(id) {
        try {
            await api.post(`/api/task-matches/${id}/reject`, {});
            await refreshSuggestions();
        } catch (err) {
            if (typeof showToast === 'function') showToast(`Fehler: ${err.message || err}`);
        }
    }

    window.openTaskBackfillModal = openTaskBackfillModal;
    window.taskBackfillRecompute = taskBackfillRecompute;
    window.taskBackfillAutoApply = taskBackfillAutoApply;
    window.taskBackfillApprove = taskBackfillApprove;
    window.taskBackfillReject = taskBackfillReject;
})();
