/* Session Detail - Table of Contents Sidebar */

function getTocPreview(msg) {
    const raw = (msg.content || '').trim();
    if (!raw) return '';
    const lines = raw.split('\n');
    for (const line of lines) {
        const clean = line.replace(/^[#*\->\s`_\[\]]+/, '').trim();
        if (clean.length > 8) return clean.substring(0, 60);
    }
    return lines[0].replace(/[#*`_\[\]]/g, '').trim().substring(0, 60);
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

    let html = '';
    let msgIndex = 0;
    let turnNum = 0;

    messages.forEach((msg) => {
        if (msg.type === 'system') return;

        const preview = getTocPreview(msg);
        const tools = getToolNames(msg);
        const isToolResult = msg.is_tool_result || (msg.type === 'user' && msg.content_json);

        // Skip tool-result User messages (docker output, grep results etc.)
        if (isToolResult) { msgIndex++; return; }
        // Skip empty messages
        if (!preview && tools.length === 0) { msgIndex++; return; }

        if (msg.type === 'user' && preview) {
            turnNum++;
            html += `<a class="toc-item toc-item-user" data-toc-target="msg-${msgIndex}" onclick="scrollToMsg(${msgIndex})">`;
            html += `<span class="toc-num">${turnNum}</span>`;
            html += `<span class="toc-text">${escapeHtml(preview)}</span>`;
            html += `</a>`;
        } else if (msg.type === 'assistant') {
            if (!preview && tools.length === 0) { msgIndex++; return; }
            html += `<a class="toc-item toc-item-assistant" data-toc-target="msg-${msgIndex}" onclick="scrollToMsg(${msgIndex})">`;
            if (preview) {
                html += `<span class="toc-text">${escapeHtml(preview)}</span>`;
            }
            if (tools.length > 0) {
                const toolStr = tools.length <= 3
                    ? tools.join(', ')
                    : tools.slice(0, 2).join(', ') + ' +' + (tools.length - 2);
                html += `<span class="toc-tools">${escapeHtml(toolStr)}</span>`;
            }
            html += `</a>`;
        }
        msgIndex++;
    });

    nav.innerHTML = html;
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
