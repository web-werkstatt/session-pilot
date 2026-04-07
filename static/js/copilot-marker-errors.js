/* Copilot Marker Parse Errors Banner (Issue #19)
 *
 * Wird vor copilot_board.js geladen. Stellt _renderMarkerParseErrors global bereit,
 * sodass _loadSections() in copilot_board.js den Banner ueber das Board zeichnen kann.
 */

function _renderMarkerParseErrors(errors) {
    var hostId = 'markerParseErrorsBanner';
    var existing = document.getElementById(hostId);
    if (!errors || !errors.length) {
        if (existing) existing.remove();
        return;
    }
    var html = '<div id="' + hostId + '" class="marker-parse-errors-banner">'
        + '<div class="marker-parse-errors-title">⚠ ' + errors.length + ' fehlerhafter Marker-Block' + (errors.length === 1 ? '' : 'e') + ' in handoff.md</div>'
        + '<ul class="marker-parse-errors-list">';
    errors.forEach(function(e) {
        var mid = escapeHtml(e.marker_id || '<unknown>');
        var et = escapeHtml(e.error_type || '');
        var em = escapeHtml(e.error || '');
        var hp = escapeHtml(e.handoff_path || '');
        html += '<li><strong>' + mid + '</strong> <span class="marker-parse-errors-type">[' + et + ']</span><br>'
             + '<span class="marker-parse-errors-msg">' + em + '</span><br>'
             + '<span class="marker-parse-errors-path">' + hp + '</span></li>';
    });
    html += '</ul></div>';
    if (existing) {
        existing.outerHTML = html;
    } else {
        var board = document.getElementById('sectionsBoard');
        if (board && board.parentNode) {
            board.parentNode.insertBefore(_markerErrorsHtmlToNode(html), board);
        }
    }
}

function _markerErrorsHtmlToNode(html) {
    var tmp = document.createElement('div');
    tmp.innerHTML = html.trim();
    return tmp.firstChild;
}
