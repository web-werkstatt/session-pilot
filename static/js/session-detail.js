function setWidth(val) {
    const conv = document.getElementById('conversation');
    if (val >= 1760) {
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
    const saved = localStorage.getItem('session-width') || '1120';
    setWidth(saved);
})();

let currentOutcome = null;
let sessionData = null;
let sessionReviews = [];
let projectThreads = [];
let relatedThreadSessions = [];
let reviewPrefill = '';

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text == null ? '' : text;
    return d.innerHTML;
}

function formatTokens(n) {
    if (!n) return '0';
    if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
    if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
    return String(n);
}

function formatDateTime(value) {
    return value ? new Date(value).toLocaleString('de-DE') : '-';
}

function formatDateShort(value) {
    return value ? new Date(value).toLocaleDateString('de-DE') : '-';
}

function formatModel(model) {
    return (model || '-').replace('claude-', '');
}

function formatOutcomeLabel(outcome) {
    if (!outcome) return 'Offen';
    return outcome.replace('_', ' ');
}

function renderMarkdown(text) {
    if (!text) return '';
    if (typeof marked === 'undefined') return '<pre>' + escapeHtml(text) + '</pre>';
    let html = marked.parse(escapeHtml(text), {breaks: true, gfm: true});
    html = html.replace(/<pre><code([\s\S]*?)>([\s\S]*?)<\/code><\/pre>/g, (m, attrs, code) => {
        return `<div class="pre-wrap"><button class="btn-copy-code" onclick="copyCode(this)">Kopieren</button><pre><code${attrs}>${code}</code></pre></div>`;
    });
    return html;
}

function summarizeValue(value) {
    const text = typeof value === 'string' ? value : JSON.stringify(value || {});
    return text.replace(/\s+/g, ' ').trim().substring(0, 90) || 'Keine Details';
}

function renderToolCard(kind, title, meta, content, openByDefault) {
    const kindClass = kind === 'result' ? 'tool-card tool-card-result' : 'tool-card';
    const icon = kind === 'result' ? '↳' : '⌘';
    const openAttr = openByDefault ? ' open' : '';
    return `<details class="${kindClass}"${openAttr}><summary><span class="tool-card-title"><span class="tool-card-icon">${icon}</span><span class="tool-card-label"><span class="tool-card-name">${escapeHtml(title)}</span><span class="tool-card-meta">${escapeHtml(meta)}</span></span></span><span class="tool-card-arrow">▾</span></summary><div class="tool-content"><pre>${escapeHtml(content)}</pre></div></details>`;
}

function renderToolUse(contentJson) {
    if (!contentJson) return '';
    let blocks;
    try {
        blocks = typeof contentJson === 'string' ? JSON.parse(contentJson) : contentJson;
    } catch {
        return '';
    }
    if (!Array.isArray(blocks)) return '';

    let html = '';
    for (const block of blocks) {
        if (block.type === 'tool_use') {
            const name = block.name || 'Tool';
            const input = block.input || {};
            html += renderToolCard('use', name, summarizeValue(input), JSON.stringify(input, null, 2), false);
        } else if (block.type === 'tool_result') {
            const content = typeof block.content === 'string' ? block.content : JSON.stringify(block.content || '', null, 2);
            const prefix = block.is_error ? 'Fehler' : 'Ergebnis';
            html += renderToolCard('result', prefix, summarizeValue(content), content, !!block.is_error);
        }
    }
    return html;
}

function getLinkedThreadIds() {
    const ids = [];
    sessionReviews.forEach(review => {
        if (review.thread_id && !ids.includes(review.thread_id)) ids.push(review.thread_id);
    });
    return ids;
}

function getSelectedThreadId() {
    const select = document.getElementById('reviewThreadSelect');
    if (!select) return null;
    const value = select.value;
    return value ? Number(value) : null;
}

function getSelectedThreadTitle() {
    const input = document.getElementById('reviewThreadTitle');
    return input ? input.value.trim() : '';
}

function setSessionHeader(session, messages) {
    const title = session.project_name || 'Unbenannte Session';
    const subtitle = `${formatDateTime(session.started_at)} · ${session.duration_formatted || '-'} · ${formatModel(session.model)} · ${session.account || '-'}`;
    document.getElementById('sessionTitle').textContent = title;
    document.getElementById('sessionSubtitle').textContent = subtitle;

    const linkedThreadCount = getLinkedThreadIds().length;
    const stats = [
        {label: 'Nachrichten', value: String(messages.length), sub: `${session.user_message_count || 0} User · ${session.assistant_message_count || 0} Assistant`},
        {label: 'Token Output', value: formatTokens(session.total_output_tokens), sub: `Input ${formatTokens(session.total_input_tokens)}`},
        {label: 'Threads', value: linkedThreadCount ? String(linkedThreadCount) : '0', sub: linkedThreadCount ? 'Mit anderen Sessions verknüpft' : 'Noch keine Verknüpfung'},
        {label: 'Outcome', value: formatOutcomeLabel(session.outcome), sub: session.outcome_note || 'Noch keine Review-Notiz'}
    ];
    document.getElementById('heroStats').innerHTML = stats.map(stat =>
        `<div class="hero-stat"><div class="hero-stat-label">${stat.label}</div><div class="hero-stat-value">${escapeHtml(stat.value)}</div><div class="hero-stat-sub">${escapeHtml(stat.sub)}</div></div>`
    ).join('');
}

function renderMeta(session) {
    const metaItems = [
        ['Account', session.account],
        ['Start', formatDateTime(session.started_at)],
        ['Ende', formatDateTime(session.ended_at)],
        ['Dauer', session.duration_formatted],
        ['Model', formatModel(session.model)],
        ['Input', formatTokens(session.total_input_tokens)],
        ['Output', formatTokens(session.total_output_tokens)],
        ['Branch', session.git_branch || '-'],
        ['Version', session.claude_version || '-'],
        ['Slug', session.slug || '-']
    ];
    const html = metaItems.map(([label, value]) =>
        `<div class="meta-item"><span class="meta-label">${label}</span><span class="meta-value">${escapeHtml(value || '-')}</span></div>`
    ).join('');
    const modalTarget = document.getElementById('metaBarModal');
    if (modalTarget) modalTarget.innerHTML = html;
}

function renderMessageStats(messages) {
    const counts = {user: 0, assistant: 0, system: 0, tool: 0};
    messages.forEach(msg => {
        if (msg.type === 'user') counts.user += 1;
        else if (msg.type === 'assistant') counts.assistant += 1;
        else if (msg.type === 'system') counts.system += 1;
        if (msg.content_json) {
            try {
                const blocks = typeof msg.content_json === 'string' ? JSON.parse(msg.content_json) : msg.content_json;
                if (Array.isArray(blocks)) {
                    counts.tool += blocks.filter(block => block.type === 'tool_use' || block.type === 'tool_result').length;
                }
            } catch {}
        }
    });

    const items = [
        ['user', 'User Turns', counts.user],
        ['assistant', 'Assistant Turns', counts.assistant],
        ['system', 'System Events', counts.system],
        ['tool', 'Tool Blocks', counts.tool]
    ];

    document.getElementById('messageStats').innerHTML = items.map(([kind, label, value]) =>
        `<div class="message-stat message-stat-${kind}"><span class="message-stat-dot"></span><span class="message-stat-label">${label}</span><span class="message-stat-value">${value}</span></div>`
    ).join('');
}

function renderReviewSummary(session, reviews) {
    const latest = reviews && reviews.length ? reviews[0] : null;
    const summary = [
        ['Status', formatOutcomeLabel(session.outcome)],
        ['Notizen', String(reviews.length)],
        ['Letzter Eintrag', latest ? formatDateTime(latest.created_at) : 'Noch keiner'],
        ['Zuletzt', latest ? latest.note : (session.outcome_note || 'Noch keine Review-Notiz')]
    ];
    document.getElementById('reviewSummary').innerHTML = summary.map(([label, value], index) => {
        const extraClass = index === 3 ? ' review-summary-item-wide' : '';
        return `<div class="review-summary-item${extraClass}"><span class="review-summary-label">${label}</span><span class="review-summary-value">${escapeHtml(value)}</span></div>`;
    }).join('');
}

function renderLinkedThreads() {
    const el = document.getElementById('linkedThreads');
    if (!el) return;
    const linkedIds = getLinkedThreadIds();
    if (!linkedIds.length) {
        el.innerHTML = '<div class="review-empty">Noch kein Thread mit anderen Sessions verknüpft.</div>';
        return;
    }
    const linked = projectThreads.filter(thread => linkedIds.includes(thread.id));
    el.innerHTML = linked.map(thread =>
        `<div class="thread-chip"><span class="thread-chip-title">${escapeHtml(thread.title)}</span><span class="thread-chip-meta">${thread.session_count || 0} Sessions · ${thread.note_count || 0} Notizen</span></div>`
    ).join('');
}

function renderRelatedThreadSessions() {
    const el = document.getElementById('relatedThreadSessions');
    if (!el) return;
    if (!relatedThreadSessions.length) {
        el.innerHTML = '<div class="review-empty">Keine weiteren Sessions aus den verknüpften Threads.</div>';
        return;
    }
    const items = relatedThreadSessions.slice(0, 8);
    el.innerHTML = '<div class="related-thread-head">Verknüpfte Sessions</div>' + items.map(item =>
        `<a class="related-session-item" href="/sessions/${encodeURIComponent(item.session_uuid)}"><span class="related-session-thread">${escapeHtml(item.thread_title)}</span><span class="related-session-date">${escapeHtml(formatDateShort(item.started_at))}</span><span class="related-session-meta">${escapeHtml(item.duration_formatted || '-')} · ${escapeHtml(formatOutcomeLabel(item.outcome))}</span></a>`
    ).join('');
}

function renderReviewHistory(reviews) {
    const el = document.getElementById('reviewHistory');
    if (!el) return;
    if (!reviews || !reviews.length) {
        el.innerHTML = '<div class="review-empty">Noch keine Review-Notizen vorhanden.</div>';
        return;
    }
    el.innerHTML = reviews.map(review => {
        const badge = review.outcome_snapshot ? `<span class="review-badge review-badge-${review.outcome_snapshot}">${escapeHtml(formatOutcomeLabel(review.outcome_snapshot))}</span>` : '';
        const thread = review.thread_title ? `<span class="review-thread-link">${escapeHtml(review.thread_title)}</span>` : '';
        return `<article class="review-entry"><div class="review-entry-head"><div class="review-entry-meta"><span>${escapeHtml(review.author || 'local')}</span><span>${escapeHtml(formatDateTime(review.created_at))}</span>${thread}</div>${badge}</div><div class="review-entry-note">${escapeHtml(review.note)}</div></article>`;
    }).join('');
}

function populateThreadSelect(preferredId) {
    const select = document.getElementById('reviewThreadSelect');
    if (!select) return;
    const options = ['<option value="">Ohne Thread speichern</option>'];
    projectThreads.forEach(thread => {
        const selected = preferredId && Number(preferredId) === Number(thread.id) ? ' selected' : '';
        options.push(`<option value="${thread.id}"${selected}>${escapeHtml(thread.title)} (${thread.session_count || 0} Sessions)</option>`);
    });
    select.innerHTML = options.join('');
}

function refreshReviewUI() {
    if (!sessionData) return;
    renderReviewSummary(sessionData, sessionReviews);
    renderLinkedThreads();
    renderRelatedThreadSessions();
    renderReviewHistory(sessionReviews);
    setSessionHeader(sessionData, window._messages || []);
    if (sessionData.outcome) highlightOutcome(sessionData.outcome);
    populateThreadSelect(getSelectedThreadId());
}

async function loadSession() {
    try {
        const r = await fetch(`/api/sessions/${SESSION_UUID}`);
        if (!r.ok) {
            document.getElementById('conversation').innerHTML = '<div class="loading">Session nicht gefunden</div>';
            return;
        }
        const d = await r.json();
        sessionData = d.session;
        sessionReviews = d.reviews || [];
        projectThreads = d.threads || [];
        relatedThreadSessions = d.related_sessions || [];

        document.title = `${sessionData.project_name || 'Session'} - Dashboard`;
        setSessionHeader(sessionData, d.messages || []);
        renderMeta(sessionData);
        renderMessageStats(d.messages || []);
        renderReviewSummary(sessionData, sessionReviews);
        renderLinkedThreads();
        renderRelatedThreadSessions();
        renderReviewHistory(sessionReviews);
        populateThreadSelect(getLinkedThreadIds()[0]);

        ['Json', 'Md', 'Html', 'Xlsx', 'Txt'].forEach(fmt => {
            document.getElementById('exp' + fmt).href = `/api/sessions/${SESSION_UUID}/export?format=${fmt.toLowerCase()}`;
            document.getElementById('exp' + fmt + '2').href = `/api/sessions/${SESSION_UUID}/export?format=${fmt.toLowerCase()}`;
        });

        currentOutcome = sessionData.outcome || null;
        if (currentOutcome) highlightOutcome(currentOutcome);
        renderMessages(d.messages || []);
    } catch (e) {
        console.error(e);
        document.getElementById('conversation').innerHTML = '<div class="loading">Fehler beim Laden</div>';
    }
}

function renderMessages(messages) {
    const conv = document.getElementById('conversation');
    if (!messages || !messages.length) {
        conv.innerHTML = '<div class="loading">Keine Nachrichten</div>';
        return;
    }

    let html = '';
    messages.forEach((msg, index) => {
        if (msg.type === 'system') {
            html += `<div class="msg-system">${escapeHtml(msg.content || '')}</div>`;
            return;
        }

        const cls = msg.type === 'user' ? 'msg-user' : 'msg-assistant';
        const role = msg.type === 'user' ? 'User' : 'Assistant';
        let contentHtml = '';

        if (msg.content) {
            contentHtml += `<div class="msg-content">${renderMarkdown(msg.content)}</div>`;
        }
        if (msg.content_json) {
            contentHtml += renderToolUse(msg.content_json);
        }

        html += `<article class="msg ${cls}"><div class="msg-role"><span>${role}</span><div class="msg-actions"><button class="btn-copy" onclick="openReviewFromMessage(${index})">Review</button><button class="btn-copy" onclick="copyMsg(this, ${index})">Kopieren</button></div></div>${contentHtml}</article>`;
    });

    conv.innerHTML = html;
    window._messages = messages;
}

function stripLineNumbers(text) {
    return text.replace(/^[ \t]*\d+[→\t]/gm, '');
}

function copyToClipboard(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = 'Kopiert!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = 'Kopieren';
            btn.classList.remove('copied');
        }, 1500);
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

function highlightOutcome(outcome) {
    currentOutcome = outcome;
    document.querySelectorAll('.outcome-btn').forEach(button => {
        button.className = 'outcome-btn';
        if (button.dataset.outcome === outcome) button.classList.add('active-' + outcome);
    });
}

function openReviewModal(prefillText) {
    const modal = document.getElementById('reviewModal');
    if (!modal) return;
    modal.classList.add('show');
    if (typeof prefillText === 'string') reviewPrefill = prefillText;
    if (reviewPrefill) {
        document.getElementById('outcomeNote').value = reviewPrefill;
        reviewPrefill = '';
    }
}

function closeReviewModal() {
    const modal = document.getElementById('reviewModal');
    if (!modal) return;
    modal.classList.remove('show');
}

function openSnapshotModal() {
    const modal = document.getElementById('snapshotModal');
    if (!modal) return;
    modal.classList.add('show');
}

function closeSnapshotModal() {
    const modal = document.getElementById('snapshotModal');
    if (!modal) return;
    modal.classList.remove('show');
}

function openReviewFromMessage(idx) {
    const msg = (window._messages || [])[idx];
    if (!msg) return;
    const snippet = stripLineNumbers((msg.content || '').trim()).replace(/\s+/g, ' ').substring(0, 280);
    const role = msg.type === 'user' ? 'User' : 'Assistant';
    openReviewModal(`[${role}-Block]\n${snippet}${snippet.length >= 280 ? '…' : ''}`);
}

async function ensureThreadSelection() {
    const threadId = getSelectedThreadId();
    const threadTitle = getSelectedThreadTitle();
    if (threadTitle) return {thread_id: null, thread_title: threadTitle};
    if (threadId) return {thread_id: threadId, thread_title: ''};
    return {thread_id: null, thread_title: ''};
}

async function saveOutcomeOnly() {
    try {
        const threadPayload = await ensureThreadSelection();
        const r = await fetch(`/api/sessions/${SESSION_UUID}/outcome`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({outcome: currentOutcome, note: '', author: 'local', ...threadPayload})
        });
        const data = await r.json();
        if (!r.ok || !data.success) throw new Error(data.error || 'Status konnte nicht gespeichert werden');
        if (sessionData) sessionData.outcome = currentOutcome;
        await reloadReviewData();
        showSaved();
    } catch (e) {
        console.error(e);
    }
}

async function addReviewNote() {
    const input = document.getElementById('outcomeNote');
    const note = (input.value || '').trim();
    if (!note) return;
    try {
        const threadPayload = await ensureThreadSelection();
        const r = await fetch(`/api/sessions/${SESSION_UUID}/reviews`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({outcome: currentOutcome, note, author: 'local', ...threadPayload})
        });
        const data = await r.json();
        if (!r.ok || !data.success) throw new Error(data.error || 'Notiz konnte nicht gespeichert werden');
        input.value = '';
        document.getElementById('reviewThreadTitle').value = '';
        if (sessionData) {
            sessionData.outcome = currentOutcome;
            sessionData.outcome_note = note;
        }
        await reloadReviewData();
        showSaved();
    } catch (e) {
        console.error(e);
    }
}

async function reloadReviewData() {
    const r = await fetch(`/api/sessions/${SESSION_UUID}`);
    const data = await r.json();
    sessionData = data.session;
    sessionReviews = data.reviews || [];
    projectThreads = data.threads || [];
    relatedThreadSessions = data.related_sessions || [];
    refreshReviewUI();
}

function showSaved() {
    const el = document.getElementById('outcomeSaved');
    if (!el) return;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 1800);
}

loadSession();
