/**
 * LLM Command Hub
 *
 * Laedt Commands, zeigt Command-Cards, fuehrt aus, zeigt Run-Historie.
 */
(function () {
    'use strict';

    var _commands = [];

    // -----------------------------------------------------------------------
    // Init
    // -----------------------------------------------------------------------

    function init() {
        loadCommands();
        loadRecentRuns();
    }

    // -----------------------------------------------------------------------
    // Commands laden + Cards rendern
    // -----------------------------------------------------------------------

    async function loadCommands() {
        try {
            var data = await api.get('/api/llm/commands');
            _commands = data.commands || [];
            renderCommandCards(_commands);
            populateDropdown(_commands);
        } catch (e) {
            document.getElementById('cmdCards').innerHTML =
                '<div class="llm-empty">Keine Commands gefunden</div>';
        }
    }

    var CMD_ICONS = {
        'audit-summary': 'scan-search',
        'governance-recommendation': 'shield-check',
        'risk-files': 'alert-triangle',
    };

    function renderCommandCards(commands) {
        var el = document.getElementById('cmdCards');
        if (!commands.length) {
            el.innerHTML = '<div class="llm-empty">Keine Commands verfuegbar. Commands sind Markdown-Dateien im prompts/ Verzeichnis.</div>';
            return;
        }

        el.innerHTML = commands.map(function (cmd) {
            var icon = CMD_ICONS[cmd.command_id] || 'terminal';
            var params = (cmd.parameters || []).map(function (p) {
                return p.name + (p.required ? ' *' : '');
            }).join(', ');

            return '<div class="cmd-card" onclick="selectCommand(\'' + esc(cmd.command_id) + '\')">' +
                '<div class="cmd-card__icon"><i data-lucide="' + icon + '"></i></div>' +
                '<div class="cmd-card__body">' +
                    '<div class="cmd-card__title">' + esc(cmd.title) + '</div>' +
                    '<div class="cmd-card__purpose">' + esc(cmd.purpose || '') + '</div>' +
                    (params ? '<div class="cmd-card__params">Parameter: ' + esc(params) + '</div>' : '') +
                '</div>' +
            '</div>';
        }).join('');

        // Lucide-Icons initialisieren
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    function populateDropdown(commands) {
        var sel = document.getElementById('cmdSelect');
        commands.forEach(function (cmd) {
            var opt = document.createElement('option');
            opt.value = cmd.command_id;
            opt.textContent = cmd.title + ' (' + cmd.command_id + ')';
            sel.appendChild(opt);
        });
    }

    window.selectCommand = function (cmdId) {
        document.getElementById('cmdSelect').value = cmdId;
        onCommandSelect();
        document.querySelector('.llm-run-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
    };

    // -----------------------------------------------------------------------
    // Command-Auswahl
    // -----------------------------------------------------------------------

    window.onCommandSelect = function () {
        var cmdId = document.getElementById('cmdSelect').value;
        var cmd = _commands.find(function (c) { return c.command_id === cmdId; });
        var paramsDiv = document.getElementById('cmdParams');
        var purposeDiv = document.getElementById('cmdPurpose');
        var hintEl = document.getElementById('cmdSelectedHint');
        var btn = document.getElementById('btnRunCmd');

        paramsDiv.innerHTML = '';

        if (!cmd) {
            purposeDiv.style.display = 'none';
            document.getElementById('userTextRow').style.display = 'none';
            hintEl.textContent = '';
            btn.disabled = true;
            return;
        }

        purposeDiv.textContent = cmd.purpose;
        purposeDiv.style.display = 'block';
        document.getElementById('userTextRow').style.display = 'block';
        hintEl.textContent = cmd.title + ' ausgewaehlt';
        btn.disabled = false;

        (cmd.parameters || []).forEach(function (p) {
            var row = document.createElement('div');
            row.className = 'form-row';
            row.innerHTML =
                '<label for="param_' + esc(p.name) + '">' + esc(p.name) +
                (p.required ? ' <span class="form-required">*</span>' : '') + '</label>' +
                '<input type="text" id="param_' + esc(p.name) + '" ' +
                'placeholder="' + esc(p.description || '') + '" ' +
                'data-param="' + esc(p.name) + '" class="llm-input">' +
                (p.description ? '<span class="form-hint">' + esc(p.description) + '</span>' : '');
            paramsDiv.appendChild(row);
        });
    };

    // -----------------------------------------------------------------------
    // Command ausfuehren
    // -----------------------------------------------------------------------

    window.runCommand = async function () {
        var cmdId = document.getElementById('cmdSelect').value;
        if (!cmdId) return;

        var context = {};
        document.querySelectorAll('#cmdParams input[data-param]').forEach(function (input) {
            context[input.dataset.param] = input.value.trim();
        });

        var userText = document.getElementById('cmdUserText').value.trim() || null;

        var cmd = _commands.find(function (c) { return c.command_id === cmdId; });
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
    };

    // -----------------------------------------------------------------------
    // Result rendern
    // -----------------------------------------------------------------------

    function _renderResult(data) {
        var resultDiv = document.getElementById('cmdResult');
        resultDiv.style.display = 'block';
        resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });

        var statusCls = data.status === 'success' ? 'run-success' : 'run-failure';
        var meta = '<span class="' + statusCls + '">' + esc(data.status) + '</span>';
        meta += ' | Run #' + data.run_id;
        if (data.model) meta += ' | ' + esc(data.model);
        if (data.duration_ms != null) meta += ' | ' + data.duration_ms + 'ms';
        document.getElementById('cmdResultMeta').innerHTML = meta;

        var body = document.getElementById('cmdResultBody');
        if (data.status === 'success' && data.output_text) {
            if (typeof marked !== 'undefined') {
                body.innerHTML = marked.parse(data.output_text, { breaks: true, gfm: true });
            } else {
                body.innerHTML = '<pre>' + esc(data.output_text) + '</pre>';
            }
        } else if (data.error_info) {
            body.innerHTML = '<div class="cmd-error-result">' + esc(data.error_info) + '</div>';
        } else {
            body.innerHTML = '<p class="llm-empty">Keine Ausgabe.</p>';
        }
    }

    // -----------------------------------------------------------------------
    // Recent Runs
    // -----------------------------------------------------------------------

    async function loadRecentRuns() {
        try {
            var data = await api.get('/api/llm/commands/runs?limit=10');
            var container = document.getElementById('recentRuns');
            var runs = data.runs || [];

            if (!runs.length) {
                container.innerHTML = '<div class="llm-empty">Noch keine Commands ausgefuehrt</div>';
                return;
            }

            var rows = runs.map(function (r) {
                var statusCls = r.status === 'success' ? 'run-success' : 'run-failure';
                return '<tr class="run-row" onclick="expandRun(this)">' +
                    '<td><span class="' + statusCls + '">' + esc(r.status) + '</span></td>' +
                    '<td class="run-cmd">' + esc(r.command_id) + '</td>' +
                    '<td class="run-model">' + esc(r.model || '—') + '</td>' +
                    '<td class="run-duration">' + (r.duration_ms != null ? r.duration_ms + 'ms' : '—') + '</td>' +
                    '<td class="run-time">' + (r.created_at ? formatTimeAgo(r.created_at) : '—') + '</td>' +
                '</tr>' +
                '<tr class="run-detail" style="display:none"><td colspan="5">' +
                    '<div class="run-output">' +
                    (r.output_text
                        ? (typeof marked !== 'undefined'
                            ? marked.parse(r.output_text, { breaks: true, gfm: true })
                            : '<pre>' + esc(r.output_text) + '</pre>')
                        : esc(r.error_info || 'Keine Ausgabe')) +
                    '</div></td></tr>';
            }).join('');

            container.innerHTML = '<table class="runs-table">' +
                '<thead><tr><th>Status</th><th>Command</th><th>Model</th><th>Dauer</th><th>Wann</th></tr></thead>' +
                '<tbody>' + rows + '</tbody></table>';
        } catch (e) {
            document.getElementById('recentRuns').innerHTML =
                '<div class="llm-empty">Fehler beim Laden der Runs</div>';
        }
    }

    window.expandRun = function (row) {
        var detail = row.nextElementSibling;
        if (detail) {
            detail.style.display = detail.style.display === 'none' ? 'table-row' : 'none';
        }
    };

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    function esc(s) {
        return typeof escapeHtml === 'function' ? escapeHtml(s) : String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
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
        document.getElementById('cmdLoading').style.display = on ? 'flex' : 'none';
        document.getElementById('btnRunCmd').disabled = on;
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
