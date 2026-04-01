/**
 * Sprint D: LLM Command Hub Frontend
 */

let _commands = [];

document.addEventListener('DOMContentLoaded', function() {
    loadCommands();
    loadRecentRuns();
});

async function loadCommands() {
    try {
        const data = await api.get('/api/llm/commands');
        _commands = data.commands || [];
        const sel = document.getElementById('cmdSelect');
        _commands.forEach(function(cmd) {
            const opt = document.createElement('option');
            opt.value = cmd.command_id;
            opt.textContent = cmd.title + ' (' + cmd.command_id + ')';
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('Commands laden fehlgeschlagen:', e);
    }
}

function onCommandSelect() {
    const cmdId = document.getElementById('cmdSelect').value;
    const cmd = _commands.find(function(c) { return c.command_id === cmdId; });
    const paramsDiv = document.getElementById('cmdParams');
    const purposeDiv = document.getElementById('cmdPurpose');
    const btn = document.getElementById('btnRunCmd');

    paramsDiv.innerHTML = '';

    if (!cmd) {
        purposeDiv.style.display = 'none';
        document.getElementById('userTextRow').style.display = 'none';
        btn.disabled = true;
        return;
    }

    purposeDiv.textContent = cmd.purpose;
    purposeDiv.style.display = 'block';
    document.getElementById('userTextRow').style.display = 'block';
    btn.disabled = false;

    (cmd.parameters || []).forEach(function(p) {
        var row = document.createElement('div');
        row.className = 'form-row';
        row.innerHTML =
            '<label for="param_' + escapeHtml(p.name) + '">' + escapeHtml(p.name) +
            (p.required ? ' *' : '') + '</label>' +
            '<input type="text" id="param_' + escapeHtml(p.name) + '" ' +
            'placeholder="' + escapeHtml(p.description || '') + '" ' +
            'data-param="' + escapeHtml(p.name) + '">';
        paramsDiv.appendChild(row);
    });
}

async function runCommand() {
    var cmdId = document.getElementById('cmdSelect').value;
    if (!cmdId) return;

    // Context aus Parametern bauen
    var context = {};
    document.querySelectorAll('#cmdParams input[data-param]').forEach(function(input) {
        context[input.dataset.param] = input.value.trim();
    });

    var userText = document.getElementById('cmdUserText').value.trim() || null;

    // Validierung
    var cmd = _commands.find(function(c) { return c.command_id === cmdId; });
    if (cmd) {
        for (var i = 0; i < (cmd.parameters || []).length; i++) {
            var p = cmd.parameters[i];
            if (p.required && !context[p.name]) {
                _showCmdError('Parameter "' + p.name + '" ist erforderlich.');
                return;
            }
        }
    }

    _hideCmdError();
    _setCmdLoading(true);

    try {
        var data = await api.post('/api/llm/commands/run', {
            command_id: cmdId,
            context: context,
            user_text: userText,
        });
        _renderResult(data);
        loadRecentRuns();
    } catch (err) {
        // api.post throws on non-2xx, but 422 returns the run result
        if (err.body && err.body.run_id) {
            _renderResult(err.body);
            loadRecentRuns();
        } else {
            _showCmdError(err.body ? err.body.error : err.message);
            document.getElementById('cmdResult').style.display = 'none';
        }
    } finally {
        _setCmdLoading(false);
    }
}

function _renderResult(data) {
    var resultDiv = document.getElementById('cmdResult');
    resultDiv.style.display = 'block';

    var meta = 'Run #' + data.run_id + ' | ' + data.command_id;
    if (data.model) meta += ' | ' + data.model;
    if (data.duration_ms != null) meta += ' | ' + data.duration_ms + 'ms';
    meta += ' | ' + data.status;
    document.getElementById('cmdResultMeta').textContent = meta;

    var body = document.getElementById('cmdResultBody');
    if (data.status === 'success' && data.output_text) {
        if (typeof marked !== 'undefined') {
            body.innerHTML = marked.parse(data.output_text, { breaks: true, gfm: true });
        } else {
            body.innerHTML = '<pre>' + escapeHtml(data.output_text) + '</pre>';
        }
    } else if (data.error_info) {
        body.innerHTML = '<div class="cmd-error-result">' + escapeHtml(data.error_info) + '</div>';
    } else {
        body.innerHTML = '<p class="text-muted">Keine Ausgabe.</p>';
    }
}

async function loadRecentRuns() {
    try {
        var data = await api.get('/api/llm/commands/runs?limit=10');
        var container = document.getElementById('recentRuns');
        var runs = data.runs || [];

        if (!runs.length) {
            container.innerHTML = '<p class="text-muted">Noch keine Runs.</p>';
            return;
        }

        var html = '<table class="runs-table"><thead><tr>' +
            '<th>#</th><th>Command</th><th>Status</th><th>Model</th><th>Dauer</th><th>Zeit</th>' +
            '</tr></thead><tbody>';

        runs.forEach(function(r) {
            var statusClass = r.status === 'success' ? 'run-success' : 'run-failure';
            html += '<tr class="run-row" onclick="expandRun(this, ' + r.run_id + ')">' +
                '<td>' + r.run_id + '</td>' +
                '<td>' + escapeHtml(r.command_id) + '</td>' +
                '<td><span class="' + statusClass + '">' + r.status + '</span></td>' +
                '<td>' + escapeHtml(r.model || '-') + '</td>' +
                '<td>' + (r.duration_ms != null ? r.duration_ms + 'ms' : '-') + '</td>' +
                '<td>' + (r.created_at ? formatTimeAgo(r.created_at) : '-') + '</td>' +
                '</tr>';
            html += '<tr class="run-detail" style="display:none"><td colspan="6">' +
                '<div class="run-output">' +
                (r.output_text
                    ? (typeof marked !== 'undefined'
                        ? marked.parse(r.output_text, { breaks: true, gfm: true })
                        : '<pre>' + escapeHtml(r.output_text) + '</pre>')
                    : escapeHtml(r.error_info || 'Keine Ausgabe')) +
                '</div></td></tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (e) {
        document.getElementById('recentRuns').innerHTML = '<p class="text-muted">Fehler beim Laden.</p>';
    }
}

function expandRun(row) {
    var detail = row.nextElementSibling;
    if (detail) {
        detail.style.display = detail.style.display === 'none' ? 'table-row' : 'none';
    }
}

function _showCmdError(msg) {
    var el = document.getElementById('cmdError');
    el.textContent = msg;
    el.style.display = 'block';
}

function _hideCmdError() {
    document.getElementById('cmdError').style.display = 'none';
}

function _setCmdLoading(on) {
    document.getElementById('cmdLoading').style.display = on ? 'block' : 'none';
    document.getElementById('btnRunCmd').disabled = on;
}
