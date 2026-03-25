/* Session Detail - Table of Contents Sidebar */

function buildToc(messages) {
    const nav = document.getElementById('tocNav');
    if (!nav) return;

    let html = '';
    let msgIndex = 0;
    messages.forEach((msg) => {
        if (msg.type === 'system') return;
        const role = msg.type === 'user' ? 'User' : 'Asst';
        const roleCls = msg.type === 'user' ? 'toc-role-user' : 'toc-role-assistant';
        const itemCls = msg.type === 'user' ? 'toc-item-user' : 'toc-item-assistant';

        let preview = '';
        const raw = (msg.content || '').trim();
        const firstLine = raw.split('\n')[0].replace(/[#*`_\[\]]/g, '').trim();
        if (msg.is_tool_result || (!raw && msg.content_json)) {
            preview = '';
        } else {
            preview = firstLine.substring(0, 45);
        }
        if (!preview && !msg.content_json) preview = '...';
        html += `<a class="toc-item ${itemCls}" data-toc-target="msg-${msgIndex}" onclick="scrollToMsg(${msgIndex})"><span class="toc-role ${roleCls}">${role}</span>${preview ? `<span class="toc-preview">${escapeHtml(preview)}</span>` : ''}</a>`;

        if (msg.content_json) {
            let blocks;
            try { blocks = typeof msg.content_json === 'string' ? JSON.parse(msg.content_json) : msg.content_json; } catch { blocks = []; }
            if (Array.isArray(blocks)) {
                for (const block of blocks) {
                    if (block.type === 'tool_use' && block.name) {
                        html += `<a class="toc-item toc-item-tool" data-toc-target="msg-${msgIndex}" onclick="scrollToMsg(${msgIndex})">${escapeHtml(block.name)}</a>`;
                    }
                }
            }
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
