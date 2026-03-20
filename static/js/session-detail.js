const SESSION_UUID = "{{ session_uuid }}";

function setWidth(val) {
    const conv = document.getElementById('conversation');
    if (val >= 2400) {
        conv.style.maxWidth = '100%';
        document.getElementById('widthLabel').textContent = 'Voll';
    } else {
        conv.style.maxWidth = val + 'px';
        document.getElementById('widthLabel').textContent = val + 'px';
    }
    document.getElementById('widthSlider').value = val;
    localStorage.setItem('session-width', val);
}

(function initWidth() {
    const saved = localStorage.getItem('session-width') || '1000';
    setWidth(saved);
})();

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function renderMarkdown(text) {
    if (!text) return '';
    // Basic markdown: code blocks, inline code, bold, headers
    let html = escapeHtml(text);
    // Fenced code blocks
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code style="background:#1a1a1a;padding:2px 5px;border-radius:3px">$1</code>');
    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h4 style="margin:10px 0 5px;color:#4fc3f7">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 style="margin:10px 0 5px;color:#4fc3f7">$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2 style="margin:10px 0 5px;color:#4fc3f7">$1</h2>');
    // Line breaks
    html = html.replace(/\n/g, '<br>');
    // Fix code blocks (undo br inside pre) + wrap with copy button
    html = html.replace(/<pre><code>([\s\S]*?)<\/code><\/pre>/g, (m, code) => {
        const clean = code.replace(/<br>/g, '\n');
        return `<div class="pre-wrap"><button class="btn-copy-code" onclick="copyCode(this)">Kopieren</button><pre><code>${clean}</code></pre></div>`;
    });
    return html;
}

function renderToolUse(contentJson) {
    if (!contentJson) return '';
    let blocks;
    try { blocks = typeof contentJson === 'string' ? JSON.parse(contentJson) : contentJson; } catch { return ''; }
    if (!Array.isArray(blocks)) return '';

    let html = '';
    for (const block of blocks) {
        if (block.type === 'tool_use') {
            const name = block.name || 'Tool';
            const inputStr = JSON.stringify(block.input || {}, null, 2);
            const summary = Object.values(block.input || {}).join(' ').substring(0, 80);
            html += `<details><summary>🔧 ${escapeHtml(name)}: ${escapeHtml(summary)}...</summary><div class="tool-content">${escapeHtml(inputStr)}</div></details>`;
        } else if (block.type === 'tool_result') {
            const content = typeof block.content === 'string' ? block.content : JSON.stringify(block.content || '', null, 2);
            const preview = (typeof content === 'string' ? content : '').substring(0, 60);
            html += `<details><summary>📋 Ergebnis: ${escapeHtml(preview)}...</summary><div class="tool-content">${escapeHtml(content)}</div></details>`;
        }
    }
    return html;
}

async function loadSession() {
    try {
        const r = await fetch(`/api/sessions/${SESSION_UUID}`);
        if (!r.ok) { document.getElementById('conversation').innerHTML = '<div class="loading">Session nicht gefunden</div>'; return; }
        const d = await r.json();
        const s = d.session;

        // Page title
        document.title = `${s.project_name || 'Session'} - Dashboard`;

        // Meta
        const startDate = s.started_at ? new Date(s.started_at).toLocaleString('de-DE') : '-';
        const metaItems = [
            ['Account', s.account],
            ['Datum', startDate],
            ['Dauer', s.duration_formatted],
            ['Model', (s.model || '-').replace('claude-', '')],
            ['Input', formatTokens(s.total_input_tokens)],
            ['Output', formatTokens(s.total_output_tokens)],
            ['Branch', s.git_branch || '-'],
            ['Version', s.claude_version || '-'],
            ['Nachrichten', `${s.user_message_count || 0} / ${s.assistant_message_count || 0}`],
        ];
        document.getElementById('metaBar').innerHTML = metaItems.map(([l, v]) =>
            `<div class="meta-item"><span class="meta-label">${l}</span><span class="meta-value">${v}</span></div>`
        ).join('');

        // Export-Links (topbar)
        ['Json','Md','Html','Xlsx','Txt'].forEach(fmt => {
            document.getElementById('exp' + fmt).href = `/api/sessions/${SESSION_UUID}/export?format=${fmt.toLowerCase()}`;
        });
        // Export-Links (export-bar)
        ['Json','Md','Html','Xlsx','Txt'].forEach(fmt => {
            document.getElementById('exp' + fmt + '2').href = `/api/sessions/${SESSION_UUID}/export?format=${fmt.toLowerCase()}`;
        });

        // Outcome
        if (s.outcome) highlightOutcome(s.outcome);
        if (s.outcome_note) document.getElementById('outcomeNote').value = s.outcome_note;

        // Messages
        renderMessages(d.messages);
    } catch(e) {
        console.error(e);
        document.getElementById('conversation').innerHTML = '<div class="loading">Fehler beim Laden</div>';
    }
}

function formatTokens(n) {
    if (!n) return '0';
    if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n/1000).toFixed(1) + 'K';
    return String(n);
}

function renderMessages(messages) {
    const conv = document.getElementById('conversation');
    if (!messages || !messages.length) { conv.innerHTML = '<div class="loading">Keine Nachrichten</div>'; return; }

    let html = '';
    for (const msg of messages) {
        if (msg.type === 'system') {
            html += `<div class="msg-system">${escapeHtml(msg.content || '')}</div>`;
            continue;
        }

        const cls = msg.type === 'user' ? 'msg-user' : 'msg-assistant';
        const role = msg.type === 'user' ? 'User' : 'Assistant';

        let contentHtml = '';
        // Text content
        if (msg.content) {
            contentHtml += `<div class="msg-content">${renderMarkdown(msg.content)}</div>`;
        }
        // Tool-Use (collapsed)
        if (msg.content_json) {
            contentHtml += renderToolUse(msg.content_json);
        }

        const msgIdx = messages.indexOf(msg);
        html += `<div class="msg ${cls}"><div class="msg-role"><span>${role}</span><button class="btn-copy" onclick="copyMsg(this, ${msgIdx})">Kopieren</button></div>${contentHtml}</div>`;
    }
    conv.innerHTML = html;
    window._messages = messages;
}

function stripLineNumbers(text) {
    // Entfernt Zeilennummern-Prefixe wie "     1→", "   42→", "  100\t"
    return text.replace(/^[ \t]*\d+[→\t]/gm, '');
}

function copyToClipboard(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Kopiert!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Kopieren'; btn.classList.remove('copied'); }, 1500);
    });
}

function copyMsg(btn, idx) {
    const msg = window._messages[idx];
    copyToClipboard(btn, stripLineNumbers(msg.content || ''));
}

function copyCode(btn) {
    const pre = btn.parentElement.querySelector('code');
    copyToClipboard(btn, stripLineNumbers(pre.textContent));
}

// === Outcome ===
let currentOutcome = null;

function highlightOutcome(outcome) {
    currentOutcome = outcome;
    document.querySelectorAll('.outcome-btn').forEach(b => {
        b.className = 'outcome-btn';
        if (b.dataset.outcome === outcome) b.classList.add('active-' + outcome);
    });
}

async function setOutcome(outcome) {
    const note = document.getElementById('outcomeNote').value;
    try {
        const r = await fetch(`/api/sessions/${SESSION_UUID}/outcome`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({outcome, note})
        });
        if (r.ok) {
            highlightOutcome(outcome);
            showSaved();
        }
    } catch(e) { console.error(e); }
}

async function saveOutcomeNote() {
    if (!currentOutcome) return;
    setOutcome(currentOutcome);
}

function showSaved() {
    const el = document.getElementById('outcomeSaved');
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2000);
}

loadSession();
