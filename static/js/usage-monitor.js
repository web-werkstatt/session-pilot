/* Usage Monitor - Real-time per-account usage tracking */

function loadUsageData() {
    api.get('/api/usage-monitor')
        .then(renderUsageMonitor)
        .catch(function(err) {
            console.error('Usage monitor error:', err);
        });
}

function renderUsageMonitor(data) {
    var grid = document.getElementById('umGrid');
    var ts = document.getElementById('umLastUpdate');
    ts.textContent = new Date().toLocaleTimeString('en-US', {hour:'2-digit', minute:'2-digit', second:'2-digit'});

    if (!data.accounts || !data.accounts.length) {
        grid.innerHTML = '<div class="um-idle-text">No accounts found</div>';
        return;
    }

    grid.innerHTML = data.accounts.map(function(a) {
        return renderAccountCard(a);
    }).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function renderAccountCard(a) {
    var costBar = renderBar(a.cost_pct);
    var msgBar = renderBar(a.messages_pct);
    var resetBar = renderBar(Math.min(100, ((300 - a.window_reset_minutes) / 300) * 100));

    var planClass = 'um-plan-' + a.plan;
    var inactive = a.active ? '' : ' inactive';

    // Token formatting
    var tokStr = formatTokenCount(a.tokens_used);
    var inStr = formatTokenCount(a.input_tokens);
    var outStr = formatTokenCount(a.output_tokens);

    // Burn rate
    var burnHtml = '';
    if (a.active && a.burn_rate_tokens > 0) {
        burnHtml = '<div class="um-stats-row">' +
            '<div class="um-stat">Burn: <strong>' + formatTokenCount(a.burn_rate_tokens) + '/min</strong></div>' +
            '<div class="um-stat">Cost: <strong>$' + a.burn_rate_cost.toFixed(3) + '/min</strong></div>' +
            '<div class="um-stat">Sessions: <strong>' + a.session_count + '</strong></div>' +
            '</div>';
    }

    // Predictions
    var predHtml = '';
    if (a.active && (a.prediction_cost_min || a.prediction_msg_min)) {
        var parts = [];
        if (a.prediction_cost_min !== null) {
            var cls = a.prediction_cost_min < 30 ? 'danger' : a.prediction_cost_min < 120 ? 'warn' : 'safe';
            parts.push('<span class="' + cls + '">Cost limit in ~' + formatMinutes(a.prediction_cost_min) + '</span>');
        }
        if (a.prediction_msg_min !== null) {
            var cls2 = a.prediction_msg_min < 30 ? 'danger' : a.prediction_msg_min < 120 ? 'warn' : 'safe';
            parts.push('<span class="' + cls2 + '">Msg limit in ~' + formatMinutes(a.prediction_msg_min) + '</span>');
        }
        predHtml = '<div class="um-prediction">' + parts.join(' · ') + '</div>';
    } else if (a.active) {
        predHtml = '<div class="um-prediction"><span class="safe">Well within limits</span></div>';
    }

    // Model distribution
    var modelsHtml = '';
    if (a.models && a.models.length) {
        modelsHtml = '<div class="um-models">' + a.models.map(function(m) {
            var name = (m.model || '').replace('claude-', '').replace('gpt-', '').replace(/-20\d{6}/, '');
            var pct = a.tokens_used > 0 ? Math.round(m.tokens / a.tokens_used * 100) : 0;
            return '<span class="um-model-tag">' + escapeHtml(name) + ' ' + pct + '% · $' + m.cost.toFixed(2) + '</span>';
        }).join('') + '</div>';
    }

    // Reset timer
    var resetHtml = '';
    if (a.active) {
        resetHtml = '<div class="um-reset">Reset in <strong>' + formatMinutes(a.window_reset_minutes) + '</strong> · Active for ' + formatMinutes(a.elapsed_minutes) + '</div>';
    }

    // Plan selector
    var planSelect = '<select class="um-plan-select" onchange="changePlan(\'' + escapeHtml(a.name) + '\', this.value)">' +
        '<option value="pro"' + (a.plan === 'pro' ? ' selected' : '') + '>Pro ($18)</option>' +
        '<option value="max5"' + (a.plan === 'max5' ? ' selected' : '') + '>Max 5x ($35)</option>' +
        '<option value="max20"' + (a.plan === 'max20' ? ' selected' : '') + '>Max 20x ($140)</option>' +
        '</select>';

    if (!a.active) {
        return '<div class="um-card inactive">' +
            '<div class="um-card-header">' +
                '<span class="um-account-name">' + escapeHtml(a.name) + '</span>' +
                '<span class="um-plan-badge ' + planClass + '">' + escapeHtml(a.plan) + '</span>' +
                planSelect +
            '</div>' +
            '<div class="um-idle-text">No activity in the last 5 hours</div>' +
            '</div>';
    }

    return '<div class="um-card">' +
        '<div class="um-card-header">' +
            '<span class="um-account-name">' + escapeHtml(a.name) + '</span>' +
            '<span class="um-plan-badge ' + planClass + '">' + escapeHtml(a.plan) + '</span>' +
            planSelect +
            '<span class="um-sessions-badge">' + a.session_count + ' sessions</span>' +
        '</div>' +

        // Cost
        '<div class="um-metric">' +
            '<div class="um-metric-header">' +
                '<span class="um-metric-label">Cost</span>' +
                '<span class="um-metric-value">$' + a.cost_used.toFixed(2) + ' / $' + a.cost_limit.toFixed(0) + '  (' + a.cost_pct.toFixed(1) + '%)</span>' +
            '</div>' +
            '<div class="um-bar"><div class="um-bar-fill ' + costBar.cls + '" style="width:' + costBar.pct + '%"></div></div>' +
        '</div>' +

        // Messages
        '<div class="um-metric">' +
            '<div class="um-metric-header">' +
                '<span class="um-metric-label">Messages</span>' +
                '<span class="um-metric-value">' + a.messages_used + ' / ' + a.message_limit + '  (' + a.messages_pct.toFixed(1) + '%)</span>' +
            '</div>' +
            '<div class="um-bar"><div class="um-bar-fill ' + msgBar.cls + '" style="width:' + msgBar.pct + '%"></div></div>' +
        '</div>' +

        // Tokens
        '<div class="um-metric">' +
            '<div class="um-metric-header">' +
                '<span class="um-metric-label">Tokens</span>' +
                '<span class="um-metric-value">' + tokStr + ' (in: ' + inStr + ' · out: ' + outStr + ')</span>' +
            '</div>' +
        '</div>' +

        '<hr class="um-divider">' +
        resetHtml +
        burnHtml +
        predHtml +
        modelsHtml +
    '</div>';
}

function renderBar(pct) {
    pct = Math.max(0, Math.min(100, pct || 0));
    var cls = pct > 85 ? 'um-bar-red' : pct > 60 ? 'um-bar-yellow' : 'um-bar-green';
    return { pct: pct.toFixed(1), cls: cls };
}

function formatMinutes(min) {
    if (min === null || min === undefined) return '-';
    if (min <= 0) return 'now';
    var h = Math.floor(min / 60);
    var m = Math.round(min % 60);
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
}

function formatTokenCount(n) {
    if (!n) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return n.toString();
}

function changePlan(account, plan) {
    api.post('/api/usage-monitor/plans', { account: account, plan: plan })
        .then(function() { loadUsageData(); })
        .catch(function(err) { console.error(err); });
}

// Start
loadUsageData();
setInterval(loadUsageData, 12000);
