/* Usage Monitor - Terminal-style live tracking */

var _umWindow = 5;
var _umRefreshRate = 10;
var _umTimer = null;

function umLoad() {
    api.get('/api/usage-monitor/live?window=' + _umWindow)
        .then(umRender)
        .catch(function(err) { console.error('Usage monitor error:', err); });
}

function umChangeWindow(v) { _umWindow = parseInt(v) || 5; umLoad(); }
function umChangeRefresh(v) {
    _umRefreshRate = parseInt(v) || 10;
    if (_umTimer) clearInterval(_umTimer);
    _umTimer = setInterval(umLoad, _umRefreshRate * 1000);
}
// Plan selection removed - limits are auto-detected via P90 analysis

function umRender(data) {
    document.getElementById('umLastUpdate').textContent =
        new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
    var grid = document.getElementById('umGrid');
    if (!data.accounts || !data.accounts.length) {
        grid.innerHTML = '<div class="um-idle">No accounts found</div>';
        return;
    }
    grid.innerHTML = data.accounts.map(function(a) {
        return a.active ? umActiveCard(a) : umIdleCard(a);
    }).join('');
}

// === Idle Card ===
function umIdleCard(a) {
    return '<div class="um-monitor inactive">' +
        umBanner(a) +
        '<div class="um-idle">No activity in the last ' + (a.window_hours || 5) + ' hours</div>' +
    '</div>';
}

function umLimitsLabel(a) {
    if (a.limits_method === 'otel') {
        var age = a.otel_age_seconds ? ' \u00B7 ' + a.otel_age_seconds + 's ago' : '';
        return '\uD83D\uDCE1 Live Anthropic Data (OpenTelemetry' + age + ')';
    }
    if (a.limits_method === 'p90') {
        return '\uD83D\uDCCA Session-Based Dynamic Limits (P90 from ' + (a.limits_sample_blocks || 0) + ' blocks)';
    }
    return '\uD83D\uDCCA Default Limits (not enough data for P90)';
}

// === Active Card ===
function umActiveCard(a) {
    var b = a.burn_rate || {};
    var costPct = a.cost_pct || 0;
    var msgPct = a.messages_pct || 0;
    var tokPct = a.tokens_pct || 0;
    var resetPct = a.elapsed_minutes > 0 ? Math.min(100, (a.elapsed_minutes / (a.window_hours * 60)) * 100) : 0;
    var billable = a.billable_tokens || (a.input_tokens + a.output_tokens);

    // Model distribution - build bar segments
    var modelBar = umModelBar(a);

    return '<div class="um-monitor">' +
        umBanner(a) +

        // Dynamic Limits Section
        '<div class="um-section-head">' + umLimitsLabel(a) + '</div>' +
        '<hr class="um-sep-dashed">' +

        // Cost
        umProgressRow('\uD83D\uDCB0 Cost Usage:', costPct, '$' + a.total_cost.toFixed(2) + ' / $' + a.cost_limit) +
        // Tokens
        umProgressRow('\uD83D\uDCCA Token Usage:', tokPct, fN(billable) + ' / ' + fN(a.token_limit || 0)) +
        // Messages
        umProgressRow('\uD83D\uDCE8 Messages Usage:', msgPct, a.user_messages + ' / ' + a.message_limit) +

        '<hr class="um-sep-dashed">' +

        // Reports link
        '<div class="um-reports-link"><a href="/usage-reports">Tages-/Wochen-/Monatsberichte &rarr;</a></div>' +

        '<hr class="um-sep-dashed">' +

        // Time to Reset
        umProgressRow('\u23F1\uFE0F  Time to Reset:', resetPct, fMin(a.window_reset_minutes) + ' remaining') +

        // Model Distribution
        modelBar +

        '<hr class="um-sep">' +

        // Burn Rate + Predictions
        '<div class="um-info-grid">' +
            '<div class="um-info-col">' +
                umInfoRow('\uD83D\uDD25 Burn Rate:', fN(b.tokens_per_min) + ' tokens/min ' + umArrow(b.tokens_per_min, b.recent_tokens_per_min)) +
                umInfoRow('\uD83D\uDCB2 Cost Rate:', '$' + (b.cost_per_min || 0).toFixed(4) + '/min') +
                umInfoRow('\uD83D\uDCB2 Cost/Hour:', '$' + (b.cost_per_hour || 0).toFixed(2) + '/hr') +
                umInfoRow('\uD83D\uDD25 Recent Burn:', fN(b.recent_tokens_per_min) + ' tok/min') +
            '</div>' +
            '<div class="um-info-col">' +
                umPredRow('\uD83D\uDD2E Cost limit:', a.prediction_cost_min, a.cost_pct) +
                umPredRow('\uD83D\uDD2E Token limit:', a.prediction_tok_min, a.tokens_pct) +
                umPredRow('\uD83D\uDD2E Msg limit:', a.prediction_msg_min, a.messages_pct) +
                umInfoRow('\u23F0 Limit resets at:', a.window_reset_time ? fTime3(a.window_reset_time) : '-') +
                umInfoRow('\uD83D\uDCDD Sessions:', a.session_count + ' (' + a.api_calls + ' API calls)') +
            '</div>' +
        '</div>' +

        // Token Breakdown
        '<div class="um-token-row">' +
            umTokenCell('Input', a.input_tokens) +
            umTokenCell('Output', a.output_tokens) +
            umTokenCell('Cache Read', a.cache_read) +
            umTokenCell('Cache Create', a.cache_create) +
        '</div>' +

        // Session Blocks
        (a.blocks && a.blocks.length > 0 ? umBlocks(a) : '') +

        // Footer
        '<div class="um-footer">' +
            '<div class="um-footer-left">' +
                '<span>' + umVelocity(b.tokens_per_min) + ' ' + fTime2(new Date()) + '</span>' +
                '<span>Active session</span>' +
                '<span>Window: <strong>' + a.window_hours + 'h</strong></span>' +
            '</div>' +
            '<div class="um-footer-right">' +
                'First: <strong>' + fTime3(a.first_activity) + '</strong> &middot; ' +
                'Last: <strong>' + fTime3(a.last_activity) + '</strong>' +
            '</div>' +
        '</div>' +
    '</div>';
}

// === Components ===

function umBanner(a) {
    var method = a.limits_method === 'p90' ? 'custom' : 'default';
    return '<div class="um-banner">' +
        '<div class="um-banner-deco">\u2726 \u2727 \u2726 \u2727 CLAUDE CODE USAGE MONITOR \u2726 \u2727 \u2726 \u2727</div>' +
        '<div class="um-banner-title">' + escapeHtml(a.name) + '</div>' +
        '<div class="um-banner-sub">[ ' + method + ' | ' + Intl.DateTimeFormat().resolvedOptions().timeZone.toLowerCase() + ' ]</div>' +
    '</div>';
}

function umProgressRow(label, pct, valText) {
    pct = Math.max(0, Math.min(100, pct || 0));
    var icon = pct > 85 ? '\uD83D\uDD34' : pct > 60 ? '\uD83D\uDFE1' : '\uD83D\uDFE2';
    var barCls = pct > 85 ? 'um-bar-red' : pct > 60 ? 'um-bar-yellow' : 'um-bar-green';
    var pctStr = pct.toFixed(1) + '%';

    return '<div class="um-row">' +
        '<span class="um-row-label">' + label + '</span>' +
        '<span class="um-row-icon">' + icon + '</span>' +
        '<div class="um-row-bar"><div class="um-row-bar-fill ' + barCls + '" style="width:' + pct.toFixed(1) + '%"></div></div>' +
        '<span class="um-row-pct">' + pctStr + '</span>' +
        '<span class="um-row-values">' + valText + '</span>' +
    '</div>';
}

function umModelBar(a) {
    if (!a.models || !a.models.length) return '';
    var parts = a.models.map(function(m) {
        var name = (m.model || '').replace('claude-', '').replace(/-20\d{6,}/, '');
        return escapeHtml(name) + ' ' + m.pct.toFixed(1) + '%';
    }).join(' | ');
    // Full green bar for single model, segments for multi
    var barHtml = '<div class="um-row-bar"><div class="um-row-bar-fill um-bar-green" style="width:100%"></div></div>';
    return '<div class="um-row">' +
        '<span class="um-row-label">Model Distribution:</span>' +
        '<span class="um-row-icon">\uD83E\uDD16</span>' +
        barHtml +
        '<span class="um-row-pct"></span>' +
        '<span class="um-row-values">' + parts + '</span>' +
    '</div>';
}

function umInfoRow(label, value) {
    return '<div class="um-info-row">' +
        '<span class="um-info-label">' + label + '</span>' +
        '<span class="um-info-value">' + value + '</span>' +
    '</div>';
}

function umPredRow(label, minutes, pct) {
    var cls = 'safe';
    var text = '';
    if (pct >= 100) {
        cls = 'danger'; text = 'LIMIT REACHED';
    } else if (minutes === null || minutes === undefined) {
        cls = 'safe'; text = 'Well within limits';
    } else {
        cls = minutes < 30 ? 'danger' : minutes < 120 ? 'warn' : 'safe';
        text = 'in ~' + fMin(minutes) + ' (' + fFutureTime(minutes) + ')';
    }
    return '<div class="um-info-row">' +
        '<span class="um-info-label">' + label + '</span>' +
        '<span class="um-info-value ' + cls + '">' + text + '</span>' +
    '</div>';
}

function umTokenCell(label, value) {
    return '<div class="um-token-cell">' +
        '<div class="um-token-label">' + label + '</div>' +
        '<div class="um-token-val">' + fN(value) + '</div>' +
    '</div>';
}

function umBlocks(a) {
    var maxTok = 0;
    for (var i = 0; i < a.blocks.length; i++) {
        if (a.blocks[i].total_tokens > maxTok) maxTok = a.blocks[i].total_tokens;
    }
    var html = '<div class="um-section-head">Session Blocks (5h windows)</div><div class="um-blocks">';
    for (var i = 0; i < a.blocks.length; i++) {
        var bl = a.blocks[i];
        var pct = maxTok > 0 ? (bl.total_tokens / maxTok * 100) : 0;
        var barCls = bl.is_active ? 'um-bar-green' : 'um-bar-yellow';
        var status = bl.is_active
            ? '<span class="um-block-status-active">ACTIVE</span>'
            : '<span class="um-block-status-ended">ended</span>';
        html += '<div class="um-block">' +
            '<span class="um-block-time">' + fTime3(bl.start_time) + ' ' + status + '</span>' +
            '<div class="um-block-bar">' +
                '<div class="um-block-bar-fill ' + barCls + '" style="width:' + pct.toFixed(1) + '%"></div>' +
                '<span class="um-block-bar-text">' + fN(bl.total_tokens) + ' tok &middot; ' + bl.messages + ' msgs &middot; ' + bl.api_calls + ' calls</span>' +
            '</div>' +
            '<span class="um-block-cost">$' + bl.cost.toFixed(2) + '</span>' +
        '</div>';
    }
    return html + '</div>';
}

// Plan selection removed - limits auto-detected via P90

// === Formatters ===

function fN(n) {
    if (!n && n !== 0) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return Math.round(n).toLocaleString('en-US');
    return n.toString();
}

function fMin(min) {
    if (min === null || min === undefined) return '-';
    if (min <= 0) return 'now';
    var h = Math.floor(min / 60);
    var m = Math.round(min % 60);
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
}

function fFutureTime(min) {
    var d = new Date(Date.now() + (min || 0) * 60000);
    return d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
}

function fTime3(iso) {
    if (!iso) return '-';
    try { return new Date(iso).toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'}); }
    catch(e) { return '-'; }
}

function fTime2(d) {
    return d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}

function fTime(iso, addMin) {
    if (!iso) return '-';
    try {
        var d = new Date(iso);
        d = new Date(d.getTime() + (addMin || 0) * 60000);
        return d.toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit'});
    } catch(e) { return '-'; }
}

function umArrow(current, recent) {
    if (!recent || !current) return '';
    if (recent > current * 1.2) return '\u2B06\uFE0F';
    if (recent < current * 0.8) return '\u2B07\uFE0F';
    return '\u27A1\uFE0F';
}

function umVelocity(tokPerMin) {
    if (tokPerMin > 500000) return '\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25';
    if (tokPerMin > 100000) return '\uD83D\uDD25\uD83D\uDD25';
    if (tokPerMin > 50000) return '\uD83D\uDD25';
    if (tokPerMin > 10000) return '\u26A1';
    if (tokPerMin > 1000) return '\uD83D\uDFE2';
    return '\uD83D\uDD35';
}

// === Init ===
umLoad();
_umTimer = setInterval(umLoad, _umRefreshRate * 1000);
