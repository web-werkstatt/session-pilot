(function() {
    var WL = window.WorkflowLoop = window.WorkflowLoop || {};

    WL.data = null;
    WL.ui = {
        loadingByMarker: {},
        errorsByMarker: {},
        successByMarker: {},
        owners: {},
        blockerReasons: {},
        ratingScores: {},
        ratingComments: {},
        checklists: {}
    };

    WL.escapeJsString = function(text) {
        return String(text || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
    };

    WL.findMarker = function(markerId) {
        if (!WL.data || !Array.isArray(WL.data.marker_groups)) return null;
        for (var i = 0; i < WL.data.marker_groups.length; i += 1) {
            var group = WL.data.marker_groups[i];
            var cards = Array.isArray(group.cards) ? group.cards : [];
            for (var j = 0; j < cards.length; j += 1) {
                if (String(cards[j].marker_id) === String(markerId)) return cards[j];
            }
        }
        return null;
    };

    WL.ownerValue = function(card) {
        var markerId = String(card.marker_id || '');
        if (WL.ui.owners[markerId] !== undefined) return WL.ui.owners[markerId];
        return card.owner || '';
    };

    WL.blockerValue = function(card) {
        var markerId = String(card.marker_id || '');
        if (WL.ui.blockerReasons[markerId] !== undefined) return WL.ui.blockerReasons[markerId];
        return card.blocked_reason || '';
    };

    WL.checklistValue = function(markerId) {
        markerId = String(markerId || '');
        if (!WL.ui.checklists[markerId]) {
            WL.ui.checklists[markerId] = { context: false, result: false, next: false };
        }
        return WL.ui.checklists[markerId];
    };

    WL.statusLabel = function(marker) {
        if (marker.rating_pending) return 'Abschluss unvollstaendig';
        if (marker.status === 'in_progress') return 'Aktiv';
        if (marker.status === 'done') return 'Done';
        if (marker.status === 'blocked') return 'Blocked';
        if (marker.status === 'todo') return 'Todo';
        return marker.status || 'Todo';
    };

    WL.copilotUrl = function(planId, markerId, tab) {
        var url = '/copilot?plan_id=' + encodeURIComponent(planId) + '&project=' + encodeURIComponent(PROJECT_NAME);
        if (markerId) url += '&marker_id=' + encodeURIComponent(markerId);
        if (tab) url += '&tab=' + encodeURIComponent(tab);
        return url;
    };
})();
