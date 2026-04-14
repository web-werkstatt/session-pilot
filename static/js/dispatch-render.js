/**
 * Dispatch Render-Funktionen — ADR-002 Stufe 2a
 * Pure HTML-Template-Funktionen fuer Assignment-Cards, Reviews, Marker-Rows.
 * Extrahiert aus dispatch.js (Commit 8) wegen Dateigroessen-Limit.
 *
 * Abhaengigkeiten: base.js (escapeHtml)
 */
var DispatchRender = (function() {
    'use strict';

    function formatTime(ts) {
        if (!ts) return '';
        try {
            var d = new Date(ts);
            return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }) + ' ' +
                   d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return String(ts).substring(0, 16);
        }
    }

    function markerRow(m, assignments) {
        var markerAssignment = (assignments || []).find(function(a) {
            return a.marker_id === m.marker_id &&
                ['proposed', 'approved', 'claimed'].indexOf(a.approval_state) !== -1;
        });

        var html = '<div class="dispatch-marker-row">';
        html += '<span class="dispatch-marker-id">' + escapeHtml(m.marker_id) + '</span>';
        html += '<span class="dispatch-marker-title" title="' + escapeHtml(m.titel || '') + '">' + escapeHtml(m.titel || m.marker_id) + '</span>';
        html += '<span class="dispatch-marker-status dispatch-marker-status--' + escapeHtml(m.status || 'todo') + '">' + escapeHtml(m.status || 'todo') + '</span>';

        if (markerAssignment) {
            html += '<span class="dispatch-marker-assigned">' + escapeHtml(markerAssignment.executor_tool) + ' (' + escapeHtml(markerAssignment.approval_state) + ')</span>';
        } else {
            html += '<button class="dispatch-marker-assign-btn" onclick="Dispatch.openForm(\'' + escapeHtml(m.marker_id) + '\')">Assign</button>';
        }

        html += '</div>';
        return html;
    }

    function assignmentCard(a) {
        var html = '<div class="dispatch-assignment-card">';

        // Top row
        html += '<div class="dispatch-assignment-top">';
        html += '<span class="dispatch-assignment-id">#' + a.assignment_id + '</span>';
        html += '<span class="dispatch-assignment-tool">' + escapeHtml(a.executor_tool || '?') + '</span>';
        if (a.marker_id) {
            html += '<span class="dispatch-assignment-marker">' + escapeHtml(a.marker_id) + '</span>';
        }
        html += '<span class="dispatch-state dispatch-state--' + escapeHtml(a.approval_state) + '">' + escapeHtml(a.approval_state) + '</span>';
        html += '<span class="dispatch-risk dispatch-risk--' + escapeHtml(a.risk_level || 'medium') + '">' + escapeHtml(a.risk_level || 'medium') + '</span>';
        html += '</div>';

        // Body
        html += '<div class="dispatch-assignment-body">';

        // Meta
        html += '<div class="dispatch-assignment-meta">';
        if (a.dispatch_mode) html += '<span>Mode: ' + escapeHtml(a.dispatch_mode) + '</span>';
        if (a.created_by) html += '<span>By: ' + escapeHtml(a.created_by) + '</span>';
        if (a.created_at) html += '<span>' + formatTime(a.created_at) + '</span>';
        if (a.claimed_by) html += '<span>Claimed: ' + escapeHtml(a.claimed_by) + '</span>';
        html += '</div>';

        // Perplexity Review
        if (a.perplexity_review) {
            html += reviewBox(a.perplexity_review);
        }

        // Actions
        html += '<div class="dispatch-assignment-actions">';
        if (a.approval_state === 'proposed') {
            if (!a.perplexity_review) {
                html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.review(' + a.assignment_id + ')">Perplexity Review</button>';
            }
            html += '<button class="dispatch-btn dispatch-btn--approve" onclick="Dispatch.approve(' + a.assignment_id + ')">Approve</button>';
            html += '<button class="dispatch-btn dispatch-btn--reject" onclick="Dispatch.reject(' + a.assignment_id + ')">Reject</button>';
        }
        if (a.approval_state === 'approved') {
            html += '<button class="dispatch-btn dispatch-btn--primary" onclick="Dispatch.claim(' + a.assignment_id + ')">Claim (Manual)</button>';
            html += '<button class="dispatch-btn dispatch-btn--ghost" onclick="Dispatch.revoke(' + a.assignment_id + ')">Revoke</button>';
        }
        if (a.approval_state === 'claimed') {
            html += '<button class="dispatch-btn dispatch-btn--approve" onclick="Dispatch.complete(' + a.assignment_id + ')">Complete</button>';
            html += '<button class="dispatch-btn dispatch-btn--reject" onclick="Dispatch.fail(' + a.assignment_id + ')">Fail</button>';
        }
        html += '</div>';

        html += '</div>';
        html += '</div>';
        return html;
    }

    function reviewBox(review) {
        if (!review || review.error) {
            return '<div class="dispatch-review-box"><div class="dispatch-review-header">Perplexity Review — Error</div><div class="dispatch-review-row">' + escapeHtml(String((review && review.error) || 'error')) + '</div></div>';
        }
        var html = '<div class="dispatch-review-box"><div class="dispatch-review-header">Perplexity Review</div>';
        if (review.risk_assessment) html += '<div class="dispatch-review-row"><span class="dispatch-review-label">Risk:</span> ' + escapeHtml(String(review.risk_assessment)) + '</div>';
        if (review.tool_fit_score !== undefined) {
            var fc = review.tool_fit_score >= 70 ? '#22c55e' : review.tool_fit_score >= 40 ? '#f59e0b' : '#ef4444';
            html += '<div class="dispatch-review-row"><span class="dispatch-review-label">Tool Fit:</span> <span style="color:' + fc + ';font-weight:600">' + review.tool_fit_score + '/100</span></div>';
        }
        if (review.recommendation) html += '<div class="dispatch-review-row"><span class="dispatch-review-label">Rec:</span> <span class="dispatch-review-recommendation dispatch-review-recommendation--' + review.recommendation + '">' + escapeHtml(review.recommendation) + '</span></div>';
        if (review.reasoning) html += '<div class="dispatch-review-row" style="font-size:11px;color:rgba(148,163,184,0.6)">' + escapeHtml(String(review.reasoning)) + '</div>';
        return html + '</div>';
    }

    return {
        formatTime: formatTime,
        markerRow: markerRow,
        assignmentCard: assignmentCard,
        reviewBox: reviewBox,
    };
})();
