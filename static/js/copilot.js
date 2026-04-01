/**
 * SPEC-COPILOT-CHAT-PERPLEXITY-001: Copilot Chat Frontend
 */

let _threadId = null;

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('chatInput').focus();
});

function newThread() {
    _threadId = null;
    document.getElementById('copilotThread').value = '';
    document.getElementById('chatMessages').innerHTML = '';
    document.getElementById('chatInput').focus();
}

async function loadHistory() {
    var projectId = document.getElementById('copilotProject').value.trim() || null;
    var threadId = _threadId;

    if (!projectId && !threadId) {
        _showChatError('Projekt oder Thread angeben um Verlauf zu laden.');
        return;
    }

    var params = new URLSearchParams();
    if (projectId) params.set('project_id', projectId);
    if (threadId) params.set('thread_id', threadId);
    params.set('limit', '50');

    try {
        var data = await api.get('/api/copilot/runs?' + params.toString());
        _renderHistory(data.runs || []);
    } catch (e) {
        _showChatError('Verlauf laden fehlgeschlagen: ' + (e.message || e));
    }
}

function _renderHistory(runs) {
    var container = document.getElementById('chatMessages');
    container.innerHTML = '';

    runs.forEach(function(run) {
        if (run.user_message) {
            _appendMessage('user', run.user_message);
        }
        if (run.assistant_reply) {
            _appendMessage('assistant', run.assistant_reply);
        } else if (run.error_info) {
            _appendMessage('error', run.error_info);
        }
        // Thread-ID aus erstem Run uebernehmen
        if (run.thread_id && !_threadId) {
            _threadId = run.thread_id;
            document.getElementById('copilotThread').value = _threadId;
        }
    });

    _scrollToBottom();
}

async function sendMessage() {
    var input = document.getElementById('chatInput');
    var message = input.value.trim();
    if (!message) return;

    var projectId = document.getElementById('copilotProject').value.trim() || null;

    _hideChatError();
    _appendMessage('user', message);
    input.value = '';
    _setLoading(true);

    try {
        var body = {
            message: message,
            project_id: projectId,
        };
        if (_threadId) body.thread_id = _threadId;

        var data = await api.post('/api/copilot/chat', body);

        // Thread-ID merken
        if (data.thread_id) {
            _threadId = data.thread_id;
            document.getElementById('copilotThread').value = _threadId;
        }

        if (data.status === 'success' && data.reply) {
            _appendMessage('assistant', data.reply);
        } else if (data.error_info) {
            _appendMessage('error', data.error_info);
        }
    } catch (err) {
        if (err.body && err.body.reply) {
            _appendMessage('assistant', err.body.reply);
        } else if (err.body && err.body.error_info) {
            _appendMessage('error', err.body.error_info);
        } else {
            _appendMessage('error', err.body ? err.body.error : (err.message || 'Unbekannter Fehler'));
        }
    } finally {
        _setLoading(false);
        input.focus();
    }
}

function _appendMessage(role, text) {
    var container = document.getElementById('chatMessages');
    var div = document.createElement('div');
    div.className = 'chat-msg chat-msg--' + role;

    var label = document.createElement('div');
    label.className = 'chat-msg-label';
    label.textContent = role === 'user' ? 'Du' : role === 'assistant' ? 'Copilot' : 'Fehler';

    var body = document.createElement('div');
    body.className = 'chat-msg-body';

    if (role === 'assistant' && typeof marked !== 'undefined') {
        body.innerHTML = marked.parse(text, { breaks: true, gfm: true });
    } else {
        body.textContent = text;
    }

    div.appendChild(label);
    div.appendChild(body);
    container.appendChild(div);
    _scrollToBottom();
}

function _scrollToBottom() {
    var container = document.getElementById('chatMessages');
    container.scrollTop = container.scrollHeight;
}

function _showChatError(msg) {
    var el = document.getElementById('chatError');
    el.textContent = msg;
    el.style.display = 'block';
}

function _hideChatError() {
    document.getElementById('chatError').style.display = 'none';
}

function _setLoading(on) {
    document.getElementById('btnSend').disabled = on;
    if (on) {
        document.getElementById('btnSend').textContent = '...';
    } else {
        document.getElementById('btnSend').textContent = 'Senden';
    }
}
