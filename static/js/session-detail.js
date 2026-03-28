function setWidth(val) {
    const conv = document.getElementById('conversation');
    const label = document.getElementById('widthLabel');
    const slider = document.getElementById('widthSlider');
    if (!conv || !label || !slider) return;
    if (val >= 2400) {
        conv.style.maxWidth = '100%';
        label.textContent = 'Voll';
    } else {
        conv.style.maxWidth = val + 'px';
        label.textContent = val + 'px';
    }
    slider.value = val;
    localStorage.setItem('session-width', val);
}

(function initWidth() {
    const saved = localStorage.getItem('session-width') || '1000';
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

// formatTokens, formatDateTime: in base.js (global)

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
    let html = marked.parse(text, {breaks: true, gfm: true});
    html = html.replace(/<pre><code([\s\S]*?)>([\s\S]*?)<\/code><\/pre>/g, (_, attrs, code) => {
        return `<div class="pre-wrap"><button class="btn-copy-code" onclick="copyCode(this)">Kopieren</button><pre><code${attrs}>${code}</code></pre></div>`;
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
            const input = block.input || {};
            const inputStr = JSON.stringify(input, null, 2);
            let summary = '';
            if (input.command) summary = input.command.substring(0, 90);
            else if (input.file_path) summary = input.file_path;
            else if (input.pattern) summary = input.pattern;
            else if (input.query) summary = input.query.substring(0, 80);
            else if (input.url) summary = input.url;
            else summary = Object.values(input).join(' ').substring(0, 80);
            html += `<details><summary><strong>${escapeHtml(name)}</strong>&ensp;${escapeHtml(summary)}</summary><div class="tool-content">${escapeHtml(inputStr)}</div></details>`;
        } else if (block.type === 'tool_result') {
            const content = typeof block.content === 'string' ? block.content : JSON.stringify(block.content || '', null, 2);
            const preview = String(content).substring(0, 80);
            html += `<details><summary>Ergebnis&ensp;${escapeHtml(preview)}${content.length > 80 ? '...' : ''}</summary><div class="tool-content">${escapeHtml(content)}</div></details>`;
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
    return select.value ? Number(select.value) : null;
}

function getSelectedThreadTitle() {
    const input = document.getElementById('reviewThreadTitle');
    return input ? input.value.trim() : '';
}

function renderMeta(session) {
    const outcomeCls = session.outcome ? ` outcome-${session.outcome}` : '';
    const outcomeLabel = session.outcome ? formatOutcomeLabel(session.outcome) : '';
    const badges = [
        `<span class="meta-badge meta-badge-account">${escapeHtml(session.account || '-')}</span>`,
        `<span class="meta-badge meta-badge-model">${escapeHtml(formatModel(session.model))}</span>`,
        session.git_branch ? `<span class="meta-badge meta-badge-branch">${escapeHtml(session.git_branch)}</span>` : '',
        outcomeLabel ? `<span class="meta-badge meta-badge-outcome${outcomeCls}">${escapeHtml(outcomeLabel)}</span>` : '',
    ].filter(Boolean).join('');

    const stats = [
        ['Datum', formatDateTime(session.started_at)],
        ['Dauer', session.duration_formatted || '-'],
        ['Version', session.claude_version || '-'],
        ['Nachrichten', `${session.user_message_count || 0} / ${session.assistant_message_count || 0}`],
        ['Input', formatTokens(session.total_input_tokens)],
        ['Output', formatTokens(session.total_output_tokens)],
    ];
    const statsHtml = stats.map(([l, v]) =>
        `<div class="meta-stat"><span class="meta-stat-label">${escapeHtml(l)}</span><span class="meta-stat-value${l === 'Input' || l === 'Output' ? ' accent' : ''}">${escapeHtml(v)}</span></div>`
    ).join('');

    document.getElementById('metaBar').innerHTML = `
        <div class="meta-header">
            <span class="meta-project-name">${escapeHtml(session.project_name || 'Session')}</span>
            <div class="meta-badges">${badges}</div>
        </div>
        <div class="meta-stats">${statsHtml}</div>
    `;
}

function renderReviewSummary(session, reviews) {
    const latest = reviews && reviews.length ? reviews[0] : null;
    const summary = [
        ['Status', formatOutcomeLabel(session.outcome)],
        ['Notizen', String(reviews.length)],
        ['Zuletzt', latest ? formatDateTime(latest.created_at) : 'Noch keiner'],
        ['Hinweis', latest ? latest.note : (session.outcome_note || 'Noch keine Bewertungs-Notiz')]
    ];
    const el = document.getElementById('reviewSummary');
    if (!el) return;
    el.innerHTML = summary.map(([label, value], index) => {
        const extraClass = index === 3 ? ' review-summary-item-wide' : '';
        return `<div class="review-summary-item${extraClass}"><span class="review-summary-label">${escapeHtml(label)}</span><span class="review-summary-value">${escapeHtml(value)}</span></div>`;
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
        el.innerHTML = '';
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
        el.innerHTML = '<div class="review-empty">Noch keine Bewertungs-Notizen vorhanden.</div>';
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

function stripLineNumbers(text) {
    return String(text || '').replace(/^[ \t]*\d+[→\t]/gm, '');
}

function copyToClipboard(btn, text) {
    function onSuccess() {
        btn.textContent = 'Kopiert!';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = 'Kopieren'; btn.classList.remove('copied'); }, 1500);
    }
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(onSuccess);
    } else {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        onSuccess();
    }
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
    document.querySelectorAll('.outcome-btn').forEach(b => {
        b.className = 'outcome-btn';
        if (b.dataset.outcome === outcome) b.classList.add('active-' + outcome);
    });
}

function showSaved() {
    const el = document.getElementById('outcomeSaved');
    if (!el) return;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), 2000);
}

function openBewertungModal(prefillText) {
    const modal = document.getElementById('reviewModal');
    if (!modal) return;
    if (typeof prefillText === 'string' && prefillText.trim()) {
        reviewPrefill = prefillText.trim();
    }
    const noteEl = document.getElementById('reviewModalNote');
    if (noteEl && reviewPrefill) {
        noteEl.value = reviewPrefill;
        reviewPrefill = '';
    }
    populateThreadSelect(getLinkedThreadIds()[0]);
    openModal('reviewModal');
}

function closeBewertungModal() {
    closeModal('reviewModal');
}

async function ensureThreadSelection() {
    const threadId = getSelectedThreadId();
    const threadTitle = getSelectedThreadTitle();
    if (threadTitle) return {thread_id: null, thread_title: threadTitle};
    return {thread_id: threadId, thread_title: ''};
}

async function setOutcome(outcome) {
    const note = document.getElementById('outcomeNote') ? document.getElementById('outcomeNote').value.trim() : '';
    try {
        const threadPayload = await ensureThreadSelection();
        await api.post(`/api/sessions/${SESSION_UUID}/outcome`, {outcome, note, ...threadPayload});
        {
            highlightOutcome(outcome);
            if (sessionData) {
                sessionData.outcome = outcome;
                sessionData.outcome_note = note || sessionData.outcome_note;
            }
            showSaved();
            await reloadReviewData();
        }
    } catch (e) { console.error(e); }
}

async function saveOutcomeNote() {
    if (!currentOutcome) return;
    await setOutcome(currentOutcome);
}

async function saveOutcomeOnly() {
    if (!currentOutcome) return;
    await setOutcome(currentOutcome);
}

async function addReviewNote() {
    const noteEl = document.getElementById('reviewModalNote');
    if (!noteEl) return;
    const note = noteEl.value.trim();
    if (!note) return;
    try {
        const threadPayload = await ensureThreadSelection();
        await api.post(`/api/sessions/${SESSION_UUID}/reviews`, {note, outcome: currentOutcome, ...threadPayload});
        noteEl.value = '';
        document.getElementById('outcomeNote').value = note;
        showSaved();
        await reloadReviewData();
    } catch (e) {
        console.error(e);
    }
}

async function reloadReviewData() {
    const d = await api.get(`/api/sessions/${SESSION_UUID}`);
    sessionData = d.session;
    sessionReviews = d.reviews || [];
    projectThreads = d.threads || [];
    relatedThreadSessions = d.related_sessions || [];
    if (sessionData.outcome) highlightOutcome(sessionData.outcome);
    if (document.getElementById('outcomeNote')) document.getElementById('outcomeNote').value = sessionData.outcome_note || '';
    renderMeta(sessionData);
    renderReviewSummary(sessionData, sessionReviews);
    renderLinkedThreads();
    renderRelatedThreadSessions();
    renderReviewHistory(sessionReviews);
    populateThreadSelect(getLinkedThreadIds()[0]);
}

function renderMessages(messages) {
    const conv = document.getElementById('conversation');
    if (!messages || !messages.length) { conv.innerHTML = '<div class="loading">Keine Nachrichten</div>'; return; }

    let html = '';
    let msgIndex = 0;
    messages.forEach((msg, index) => {
        if (msg.type === 'system') {
            html += `<div class="msg-system">${escapeHtml(msg.content || '')}</div>`;
            return;
        }

        const isToolResult = msg.type === 'user' && msg.content_json;
        const cls = isToolResult ? 'msg-tool-result' : msg.type === 'user' ? 'msg-user' : 'msg-assistant';
        const role = isToolResult ? 'Tool Result' : msg.type === 'user' ? 'User' : 'Assistant';

        let contentHtml = '';
        if (msg.content) {
            const rendered = msg.type === 'assistant' ? renderMarkdown(msg.content) : escapeHtml(msg.content);
            contentHtml += `<div class="msg-content">${rendered}</div>`;
        }
        if (msg.content_json) contentHtml += renderToolUse(msg.content_json);

        const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString('de-DE', {hour:'2-digit', minute:'2-digit', second:'2-digit'}) : '';
        html += `<div class="msg ${cls}" id="msg-${msgIndex}" data-msg-index="${msgIndex}"><div class="msg-role"><span>${role}${time ? `<span class="msg-time">${time}</span>` : ''}</span><span class="msg-actions"><button class="btn-copy" onclick="copyMsg(this, ${index})">Kopieren</button><button class="btn-copy" onclick="openReviewFromMessage(${index})">Bewertung</button></span></div>${contentHtml}</div>`;
        msgIndex++;
    });
    conv.innerHTML = html;
    window._messages = messages;
    buildToc(messages);
    // Lucide Icons nach grossem DOM-Rendering wiederherstellen
    requestAnimationFrame(() => { if (typeof lucide !== 'undefined') lucide.createIcons(); });
}


function openReviewFromMessage(idx) {
    const msg = (window._messages || [])[idx];
    if (!msg) return;
    const snippet = stripLineNumbers((msg.content || '').trim()).replace(/\s+/g, ' ').substring(0, 280);
    const role = msg.type === 'user' ? 'User' : 'Assistant';
    openBewertungModal(`[${role}-Block]\n${snippet}${snippet.length >= 280 ? '…' : ''}`);
}

async function loadSession() {
    try {
        const d = await api.get(`/api/sessions/${SESSION_UUID}`);
        sessionData = d.session;
        sessionReviews = d.reviews || [];
        projectThreads = d.threads || [];
        relatedThreadSessions = d.related_sessions || [];

        document.title = `${sessionData.project_name || 'Session'} - Dashboard`;
        renderMeta(sessionData);
        renderReviewSummary(sessionData, sessionReviews);
        renderLinkedThreads();
        renderRelatedThreadSessions();
        renderReviewHistory(sessionReviews);
        populateThreadSelect(getLinkedThreadIds()[0]);

        ['Json','Md','Html','Xlsx','Txt'].forEach(fmt => {
            const top = document.getElementById('exp' + fmt);
            const bottom = document.getElementById('exp' + fmt + '2');
            if (top) top.href = `/api/sessions/${SESSION_UUID}/export?format=${fmt.toLowerCase()}`;
            if (bottom) bottom.href = `/api/sessions/${SESSION_UUID}/export?format=${fmt.toLowerCase()}`;
        });

        if (sessionData.outcome) highlightOutcome(sessionData.outcome);
        if (sessionData.outcome_note && document.getElementById('outcomeNote')) document.getElementById('outcomeNote').value = sessionData.outcome_note;

        renderMessages(d.messages || []);
    } catch(e) {
        console.error(e);
        document.getElementById('conversation').innerHTML = '<div class="loading">Fehler beim Laden</div>';
    }
}

loadSession();
