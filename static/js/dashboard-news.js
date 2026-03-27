// === DASHBOARD NEWS ===
// News Ticker laden und rendern

// News Ticker laden - mit sanftem Update ohne Ruckeln
function loadNews() {
    fetch('/api/news')
        .then(r => r.json())
        .then(data => {
            // Nur aktualisieren wenn sich etwas geändert hat
            const newHash = JSON.stringify(data.headlines.map(h => h.project + h.type));
            if (newHash !== currentNewsHash) {
                currentNewsHash = newHash;
                renderNewsTicker(data.headlines);
            }
        })
        .catch(err => console.error('News laden fehlgeschlagen:', err));
}

function renderNewsTicker(headlines) {
    const container = document.getElementById('newsTickerContent');
    if (!headlines || headlines.length === 0) {
        if (container.innerHTML.includes('Lade')) {
            container.innerHTML = '<span class="news-item">Keine aktuellen Neuigkeiten</span>';
        }
        return;
    }

    // Icons für verschiedene News-Typen
    const icons = {
        'commit': 'file-text',
        'file_change': 'file',
        'new_project': 'plus-circle',
        'sync_warning': 'alert-triangle'
    };

    // Erstelle News-Items (doppelt für endlose Animation)
    let html = '';
    const items = [...headlines, ...headlines]; // Verdoppeln für nahtlose Animation
    items.forEach(news => {
        const iconName = icons[news.type] || 'pin';
        const icon = `<i data-lucide="${iconName}" style="width:14px;height:14px;display:inline-block;vertical-align:middle"></i>`;
        html += `
            <span class="news-item" onclick="window.location='/news'">
                <span class="news-icon">${icon}</span>
                <span class="news-project">${news.project}</span>
                <span class="news-message">${news.message || news.title}</span>
            </span>
        `;
    });

    // Sanftes Update: Animation kurz pausieren
    container.style.animationPlayState = 'paused';
    container.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
    // Animation nach kleinem Delay fortsetzen
    requestAnimationFrame(() => {
        container.style.animationPlayState = 'running';
    });
}
