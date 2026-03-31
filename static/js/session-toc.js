/* Session Detail - Table of Contents Sidebar */

function getTocPreview(msg) {
    const raw = (msg.content || '').trim();
    if (!raw) return '';
    const lines = raw.split('\n');
    for (const line of lines) {
        const clean = line.replace(/^[#*\->\s`_\[\]]+/, '').trim();
        if (clean.length > 8) return clean.substring(0, 40);
    }
    return lines[0].replace(/[#*`_\[\]]/g, '').trim().substring(0, 40);
}

function getToolNames(msg) {
    if (!msg.content_json) return [];
    let blocks;
    try { blocks = typeof msg.content_json === 'string' ? JSON.parse(msg.content_json) : msg.content_json; } catch { return []; }
    if (!Array.isArray(blocks)) return [];
    const names = [];
    for (const block of blocks) {
        if (block.type === 'tool_use' && block.name) names.push(block.name);
    }
    return names;
}

function buildToc(messages) {
    const nav = document.getElementById('tocNav');
    if (!nav) return;

    // Collect turns: group user message + following assistant messages
    const turns = [];
    let msgIndex = 0;
    let currentTurn = null;

    messages.forEach((msg) => {
        if (msg.type === 'system') return;
        const isToolResult = msg.is_tool_result || (msg.type === 'user' && msg.content_json);
        if (isToolResult) { msgIndex++; return; }

        if (msg.type === 'user') {
            const preview = getTocPreview(msg);
            if (preview) {
                currentTurn = { userIdx: msgIndex, preview, assistants: [] };
                turns.push(currentTurn);
            }
        } else if (msg.type === 'assistant' && currentTurn) {
            const preview = getTocPreview(msg);
            const tools = getToolNames(msg);
            if (preview || tools.length) {
                currentTurn.assistants.push({ idx: msgIndex, preview, tools });
            }
        }
        msgIndex++;
    });

    // Render: user turns with collapsible assistant details
    let html = '';
    turns.forEach((turn, i) => {
        const num = i + 1;
        const hasDetails = turn.assistants.length > 0;
        const toolCount = turn.assistants.reduce((s, a) => s + a.tools.length, 0);
        const toolBadge = toolCount > 0 ? ` <span class="toc-tool-count">${toolCount}</span>` : '';

        html += `<div class="toc-turn" data-turn="${num}">`;
        html += `<a class="toc-item toc-item-user" data-toc-target="msg-${turn.userIdx}" onclick="scrollToMsg(${turn.userIdx})">`;
        html += `<span class="toc-num">${num}</span>`;
        html += `<span class="toc-text">${escapeHtml(turn.preview)}</span>${toolBadge}`;
        html += `</a>`;

        if (hasDetails) {
            html += `<div class="toc-details">`;
            turn.assistants.forEach(a => {
                html += `<a class="toc-item toc-item-assistant" data-toc-target="msg-${a.idx}" onclick="scrollToMsg(${a.idx})">`;
                if (a.preview) html += `<span class="toc-text">${escapeHtml(a.preview)}</span>`;
                if (a.tools.length) {
                    const ts = a.tools.length <= 2 ? a.tools.join(', ') : a.tools.slice(0, 2).join(', ') + ' +' + (a.tools.length - 2);
                    html += `<span class="toc-tools">${escapeHtml(ts)}</span>`;
                }
                html += `</a>`;
            });
            html += `</div>`;
        }
        html += `</div>`;
    });

    nav.innerHTML = html;

    // Click user item toggles details
    nav.querySelectorAll('.toc-item-user').forEach(item => {
        item.addEventListener('dblclick', (e) => {
            e.preventDefault();
            const turn = item.closest('.toc-turn');
            if (turn) turn.classList.toggle('expanded');
        });
    });

    setupTocScroll();
}

function scrollToMsg(idx) {
    const el = document.getElementById('msg-' + idx);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function setupTocScroll() {
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;
    const tocItems = document.querySelectorAll('.toc-item');
    if (!tocItems.length) return;

    let ticking = false;
    mainContent.addEventListener('scroll', () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
            const msgs = document.querySelectorAll('.msg[id]');
            let activeId = null;
            const scrollTop = mainContent.scrollTop;
            const offset = 120;
            for (const msg of msgs) {
                if (msg.offsetTop - offset <= scrollTop) activeId = msg.id;
            }
            tocItems.forEach(item => {
                item.classList.toggle('active', item.dataset.tocTarget === activeId);
            });
            if (activeId) {
                const activeItem = document.querySelector(`.toc-item[data-toc-target="${activeId}"]`);
                if (activeItem) activeItem.scrollIntoView({ block: 'nearest', behavior: 'auto' });
            }
            ticking = false;
        });
    });
}
