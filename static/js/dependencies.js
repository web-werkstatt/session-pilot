let allProjects = [];
let allRelations = [];
let relationTypes = [];

// Graph state
let graphNodes = {};
let selectedNode = null;
let connectSourceNode = null;
let draggedNode = null;
let dragOffset = {x: 0, y: 0};

// Positions & Colors persistence
const STORAGE_KEY = 'dependency-graph-positions';
const COLORS_KEY = 'dependency-graph-colors';
let colorMenuTarget = null;

function loadSavedPositions() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}; }
    catch { return {}; }
}

function loadSavedColors() {
    try { return JSON.parse(localStorage.getItem(COLORS_KEY)) || {}; }
    catch { return {}; }
}

function savePositions() {
    const positions = {};
    for (const [name, node] of Object.entries(graphNodes)) {
        positions[name] = {x: node.x, y: node.y};
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(positions));
}

function saveColors() {
    const colors = {};
    for (const [name, node] of Object.entries(graphNodes)) {
        if (node.color && node.color !== '#404040') {
            colors[name] = node.color;
        }
    }
    localStorage.setItem(COLORS_KEY, JSON.stringify(colors));
}

// DATA LOADING
async function loadData() {
    const data = await api.get('/api/data');
    allProjects = data.projects.map(p => p.name).sort();

    const relData = await api.get('/api/relations');
    allRelations = relData.relations || [];
    relationTypes = relData.relation_types || [];

    populateSelects();
    renderRelations();
    updateStats();
    renderProjectList();
    renderGraphLegend();
    initGraphFromRelations();
}

function populateSelects() {
    const typeSelect = document.getElementById('relationType');
    const typeFilter = document.getElementById('typeFilter');
    const graphTypeSelect = document.getElementById('graphRelationType');
    const connectModalType = document.getElementById('connectModalType');

    const typeOptions = relationTypes.map(t =>
        `<option value="${t.id}">${renderIcon(t.icon)} ${t.name}</option>`
    ).join('');
    typeSelect.innerHTML = typeOptions;
    graphTypeSelect.innerHTML = typeOptions;
    connectModalType.innerHTML = typeOptions;

    typeFilter.innerHTML = '<option value="">All Types</option>' + typeOptions;

    document.getElementById('typeList').innerHTML = relationTypes.map(t =>
        `<span class="type-badge" style="background: ${t.color}20; border: 1px solid ${t.color};">${renderIcon(t.icon)} ${t.name}</span>`
    ).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

// AJAX AUTOCOMPLETE
let highlightedIndex = -1;
let searchDebounceTimers = {};
let currentSearchController = null;

function onProjectSearch(type) {
    const input = document.getElementById(type + 'ProjectInput');
    const hiddenInput = document.getElementById(type + 'Project');
    const searchTerm = input.value.trim();

    hiddenInput.value = '';
    input.classList.remove('has-value');

    clearTimeout(searchDebounceTimers[type]);
    searchDebounceTimers[type] = setTimeout(() => {
        fetchProjects(type, searchTerm);
    }, 200);
}

async function fetchProjects(type, query) {
    const dropdown = document.getElementById(type + 'Dropdown');

    dropdown.innerHTML = '<div class="autocomplete-loading">Searching...</div>';
    dropdown.classList.add('show');

    if (currentSearchController) {
        currentSearchController.abort();
    }
    currentSearchController = new AbortController();

    try {
        const results = await api.request(`/api/projects/search?q=${encodeURIComponent(query)}&limit=15`, {
            signal: currentSearchController.signal
        });

        if (results.length === 0) {
            dropdown.innerHTML = '<div class="autocomplete-no-results">No projects found</div>';
            return;
        }

        dropdown.innerHTML = results.map((p, i) => {
            const desc = p.description ? `<div class="project-desc">${p.description}</div>` : '';
            return `<div class="autocomplete-item" data-value="${p.name}" onclick="selectProject('${type}', '${p.name}')">
                <div class="project-name">${p.name}</div>
                ${desc}
            </div>`;
        }).join('');

        highlightedIndex = -1;
    } catch (err) {
        if (err.name !== 'AbortError') {
            dropdown.innerHTML = '<div class="autocomplete-no-results">Error loading</div>';
        }
    }
}

function selectProject(type, value) {
    const input = document.getElementById(type + 'ProjectInput');
    const dropdown = document.getElementById(type + 'Dropdown');
    const hiddenInput = document.getElementById(type + 'Project');

    input.value = value;
    hiddenInput.value = value;
    input.classList.add('has-value');
    dropdown.classList.remove('show');
}

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    const activeDropdown = document.querySelector('.autocomplete-dropdown.show');
    if (!activeDropdown) return;

    const items = activeDropdown.querySelectorAll('.autocomplete-item');
    if (items.length === 0) return;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        highlightedIndex = Math.min(highlightedIndex + 1, items.length - 1);
        updateHighlight(items);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        highlightedIndex = Math.max(highlightedIndex - 1, 0);
        updateHighlight(items);
    } else if (e.key === 'Enter' && highlightedIndex >= 0) {
        e.preventDefault();
        items[highlightedIndex].click();
    } else if (e.key === 'Escape') {
        activeDropdown.classList.remove('show');
    }
});

function updateHighlight(items) {
    items.forEach((item, i) => {
        item.classList.toggle('highlighted', i === highlightedIndex);
    });
    if (highlightedIndex >= 0) {
        items[highlightedIndex].scrollIntoView({ block: 'nearest' });
    }
}

// Close dropdown on outside click
document.addEventListener('click', (e) => {
    if (!e.target.closest('.autocomplete-wrapper')) {
        document.querySelectorAll('.autocomplete-dropdown').forEach(d => d.classList.remove('show'));
    }
});

// LIST VIEW
function renderRelations() {
    const container = document.getElementById('relationsList');
    const searchTerm = document.getElementById('searchFilter').value.toLowerCase();
    const typeFilterVal = document.getElementById('typeFilter').value;

    let filtered = allRelations;
    if (searchTerm) {
        filtered = filtered.filter(r =>
            r.source.toLowerCase().includes(searchTerm) ||
            r.target.toLowerCase().includes(searchTerm) ||
            (r.note && r.note.toLowerCase().includes(searchTerm))
        );
    }
    if (typeFilterVal) {
        filtered = filtered.filter(r => r.type === typeFilterVal);
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon"><i data-lucide="link" class="icon icon-xl"></i></div>
                <div class="empty-state-title">${allRelations.length === 0 ? 'No relations' : 'No results'}</div>
            </div>`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
        return;
    }

    container.innerHTML = filtered.map(rel => {
        const type = relationTypes.find(t => t.id === rel.type) || {icon: '', name: rel.type, color: '#666'};
        return `
            <div class="relation-card">
                <div class="relation-source" title="${rel.source}">${rel.source}</div>
                <span class="relation-arrow">&rarr;</span>
                <span class="relation-type" style="background: ${type.color}30; color: ${type.color};">${renderIcon(type.icon)} ${type.name}</span>
                <span class="relation-arrow">&rarr;</span>
                <div class="relation-target" title="${rel.target}">${rel.target}</div>
                ${rel.note ? `<span class="relation-note" title="${rel.note}">${rel.note}</span>` : ''}
                <button class="relation-delete" onclick="deleteRelation('${rel.id}')" title="Delete">&times;</button>
            </div>`;
    }).join('');
}

function filterRelations() { renderRelations(); }

function updateStats() {
    document.getElementById('totalRelations').textContent = allRelations.length;
    const linkedProjects = new Set();
    allRelations.forEach(r => { linkedProjects.add(r.source); linkedProjects.add(r.target); });
    document.getElementById('totalProjects').textContent = linkedProjects.size;

    const typeCounts = {};
    allRelations.forEach(r => { typeCounts[r.type] = (typeCounts[r.type] || 0) + 1; });
    document.getElementById('typeStats').innerHTML = relationTypes.map(t => {
        const count = typeCounts[t.id] || 0;
        if (count === 0) return '';
        return `<div class="stat"><span class="stat-value" style="color: ${t.color};">${count}</span><span class="stat-label">${t.icon} ${t.name}</span></div>`;
    }).join('');
}

