// GRAPH VIEW
function renderProjectList() {
    const container = document.getElementById('projectList');
    const search = document.getElementById('projectSearch').value.toLowerCase();

    let projects = allProjects;
    if (search) {
        projects = projects.filter(p => p.toLowerCase().includes(search));
    }

    container.innerHTML = projects.map(p => {
        const inGraph = graphNodes[p] ? 'in-graph' : '';
        return `<div class="project-item ${inGraph}" draggable="${!inGraph}" ondragstart="onProjectDragStart(event, '${p}')">${p}</div>`;
    }).join('');
}

function filterProjectList() { renderProjectList(); }

function renderGraphLegend() {
    document.getElementById('graphLegend').innerHTML = relationTypes.map(t =>
        `<div class="legend-item"><div class="legend-color" style="background: ${t.color};"></div>${t.icon} ${t.name}</div>`
    ).join('');
}

function initGraphFromRelations() {
    const savedPositions = loadSavedPositions();
    const projectsInRelations = new Set();
    allRelations.forEach(r => {
        projectsInRelations.add(r.source);
        projectsInRelations.add(r.target);
    });

    let index = 0;
    projectsInRelations.forEach(projName => {
        if (!graphNodes[projName]) {
            const saved = savedPositions[projName];
            const x = saved ? saved.x : 100 + (index % 5) * 180;
            const y = saved ? saved.y : 80 + Math.floor(index / 5) * 100;
            addNodeToGraph(projName, x, y);
            index++;
        }
    });

    drawConnections();
    renderProjectList();
}

function addNodeToGraph(projectName, x, y, color = null) {
    if (graphNodes[projectName]) return;

    const savedColors = loadSavedColors();
    const nodeColor = color || savedColors[projectName] || '#404040';

    const container = document.getElementById('graphContainer');
    const node = document.createElement('div');
    node.className = 'graph-node';
    node.style.left = x + 'px';
    node.style.top = y + 'px';
    node.style.background = nodeColor;
    node.dataset.project = projectName;

    node.innerHTML = `
        <span class="node-text">${projectName}</span>
        <button class="node-remove" onclick="removeNodeFromGraph('${projectName}')" title="Remove from graph">&times;</button>
    `;

    node.addEventListener('mousedown', (e) => onNodeMouseDown(e, projectName));
    node.addEventListener('click', (e) => onNodeClick(e, projectName));
    node.addEventListener('contextmenu', (e) => showColorMenu(e, projectName));

    container.appendChild(node);
    graphNodes[projectName] = {x, y, element: node, color: nodeColor};
    savePositions();
}

function showColorMenu(e, projectName) {
    e.preventDefault();
    e.stopPropagation();
    colorMenuTarget = projectName;
    const menu = document.getElementById('nodeColorMenu');
    const container = document.getElementById('graphContainer');
    const rect = container.getBoundingClientRect();

    menu.style.left = (e.clientX - rect.left + container.scrollLeft) + 'px';
    menu.style.top = (e.clientY - rect.top + container.scrollTop) + 'px';
    menu.classList.add('show');
}

function setNodeColor(color) {
    if (colorMenuTarget && graphNodes[colorMenuTarget]) {
        graphNodes[colorMenuTarget].color = color;
        graphNodes[colorMenuTarget].element.style.background = color;
        saveColors();
    }
    document.getElementById('nodeColorMenu').classList.remove('show');
    colorMenuTarget = null;
}

function removeNodeFromGraph(projectName) {
    if (!graphNodes[projectName]) return;
    graphNodes[projectName].element.remove();
    delete graphNodes[projectName];
    savePositions();
    saveColors();
    drawConnections();
    renderProjectList();
}

function onNodeMouseDown(e, projectName) {
    if (e.shiftKey) return;
    e.preventDefault();
    draggedNode = projectName;
    const node = graphNodes[projectName];
    dragOffset.x = e.clientX - node.x;
    dragOffset.y = e.clientY - node.y;
    node.element.classList.add('dragging');
}

function onNodeClick(e, projectName) {
    e.stopPropagation();

    if (e.shiftKey && selectedNode && selectedNode !== projectName) {
        showConnectModal(selectedNode, projectName);
        clearSelection();
        return;
    }

    clearSelection();
    selectedNode = projectName;
    graphNodes[projectName].element.classList.add('selected');
}

function clearSelection() {
    if (selectedNode && graphNodes[selectedNode]) {
        graphNodes[selectedNode].element.classList.remove('selected');
    }
    selectedNode = null;
    connectSourceNode = null;
    document.getElementById('connectInfo').classList.remove('active');
    Object.values(graphNodes).forEach(n => {
        n.element.classList.remove('connect-source', 'connect-target');
    });
}

function showConnectModal(source, target) {
    document.getElementById('connectModalInfo').textContent = `${source} \u2192 ${target}`;
    document.getElementById('connectModal').classList.add('show');
    document.getElementById('connectModal').dataset.source = source;
    document.getElementById('connectModal').dataset.target = target;
}

function hideConnectModal() {
    document.getElementById('connectModal').classList.remove('show');
}

async function confirmConnection() {
    const modal = document.getElementById('connectModal');
    const source = modal.dataset.source;
    const target = modal.dataset.target;
    const type = document.getElementById('connectModalType').value;
    const note = document.getElementById('connectModalNote').value;

    const result = await api.post('/api/relations', {source, target, type, note});
    if (result.error) {
        alert(result.error);
        return;
    }

    hideConnectModal();
    document.getElementById('connectModalNote').value = '';
    loadData();
}

function updateGraphSize() {
    let maxX = 800, maxY = 500;
    Object.values(graphNodes).forEach(node => {
        const nodeRight = node.x + (node.element.offsetWidth || 150) + 50;
        const nodeBottom = node.y + (node.element.offsetHeight || 40) + 50;
        maxX = Math.max(maxX, nodeRight);
        maxY = Math.max(maxY, nodeBottom);
    });

    const svg = document.getElementById('graphSvg');
    svg.style.width = maxX + 'px';
    svg.style.height = maxY + 'px';
}

function drawConnections() {
    updateGraphSize();
    const svg = document.getElementById('graphSvg');
    svg.querySelectorAll('line, text.edge-label').forEach(el => el.remove());

    allRelations.forEach(rel => {
        const sourceNode = graphNodes[rel.source];
        const targetNode = graphNodes[rel.target];
        if (!sourceNode || !targetNode) return;

        const type = relationTypes.find(t => t.id === rel.type) || {color: '#666'};

        const sourceEl = sourceNode.element;
        const targetEl = targetNode.element;
        const x1 = sourceNode.x + sourceEl.offsetWidth / 2;
        const y1 = sourceNode.y + sourceEl.offsetHeight / 2;
        const x2 = targetNode.x + targetEl.offsetWidth / 2;
        const y2 = targetNode.y + targetEl.offsetHeight / 2;

        const angle = Math.atan2(y2 - y1, x2 - x1);
        const sourceRadius = Math.max(sourceEl.offsetWidth, sourceEl.offsetHeight) / 2 + 5;
        const targetRadius = Math.max(targetEl.offsetWidth, targetEl.offsetHeight) / 2 + 5;

        const startX = x1 + Math.cos(angle) * sourceRadius;
        const startY = y1 + Math.sin(angle) * sourceRadius;
        const endX = x2 - Math.cos(angle) * targetRadius;
        const endY = y2 - Math.sin(angle) * targetRadius;

        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', startX);
        line.setAttribute('y1', startY);
        line.setAttribute('x2', endX);
        line.setAttribute('y2', endY);
        line.setAttribute('stroke', type.color);
        line.setAttribute('marker-end', 'url(#arrowhead)');
        line.dataset.relationId = rel.id;
        line.style.pointerEvents = 'stroke';
        line.style.cursor = 'pointer';
        line.addEventListener('dblclick', () => {
            if (confirm(`Delete relation "${rel.source} \u2192 ${rel.target}"?`)) {
                deleteRelation(rel.id);
            }
        });
        svg.appendChild(line);

        const marker = svg.querySelector('#arrowhead polygon');
        if (marker) marker.setAttribute('fill', type.color);
    });
}

// Drag & Drop from project list
function onProjectDragStart(e, projectName) {
    if (graphNodes[projectName]) {
        e.preventDefault();
        return;
    }
    e.dataTransfer.setData('text/plain', projectName);
    e.dataTransfer.effectAllowed = 'copy';
}

// Mouse move handler for node dragging
document.addEventListener('mousemove', (e) => {
    if (draggedNode && graphNodes[draggedNode]) {
        const container = document.getElementById('graphContainer');
        const rect = container.getBoundingClientRect();
        const x = e.clientX - rect.left - dragOffset.x + container.scrollLeft;
        const y = e.clientY - rect.top - dragOffset.y + container.scrollTop;

        graphNodes[draggedNode].x = Math.max(0, x);
        graphNodes[draggedNode].y = Math.max(0, y);
        graphNodes[draggedNode].element.style.left = graphNodes[draggedNode].x + 'px';
        graphNodes[draggedNode].element.style.top = graphNodes[draggedNode].y + 'px';

        drawConnections();
    }
});

document.addEventListener('mouseup', () => {
    if (draggedNode && graphNodes[draggedNode]) {
        graphNodes[draggedNode].element.classList.remove('dragging');
        savePositions();
    }
    draggedNode = null;
});

// Graph container drop zone
document.addEventListener('DOMContentLoaded', () => {
    const graphContainer = document.getElementById('graphContainer');
    if (!graphContainer) return;

    graphContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        graphContainer.classList.add('drag-over');
    });
    graphContainer.addEventListener('dragleave', () => {
        graphContainer.classList.remove('drag-over');
    });
    graphContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        graphContainer.classList.remove('drag-over');
        const projectName = e.dataTransfer.getData('text/plain');
        if (projectName && !graphNodes[projectName]) {
            const rect = graphContainer.getBoundingClientRect();
            const x = e.clientX - rect.left - 50;
            const y = e.clientY - rect.top - 15;
            addNodeToGraph(projectName, x, y);
            renderProjectList();
        }
    });

    // Click on container to deselect and close color menu
    graphContainer.addEventListener('click', (e) => {
        if (e.target === graphContainer || e.target.classList.contains('graph-node')) {
            document.getElementById('nodeColorMenu').classList.remove('show');
            colorMenuTarget = null;
        }
        if (e.target === graphContainer) {
            clearSelection();
        }
    });
});

// Escape to cancel
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        clearSelection();
        hideConnectModal();
        hideAddTypeModal();
    }
});

function autoLayoutGraph() {
    const nodes = Object.keys(graphNodes);
    const cols = Math.ceil(Math.sqrt(nodes.length));
    nodes.forEach((name, i) => {
        const x = 80 + (i % cols) * 200;
        const y = 60 + Math.floor(i / cols) * 90;
        graphNodes[name].x = x;
        graphNodes[name].y = y;
        graphNodes[name].element.style.left = x + 'px';
        graphNodes[name].element.style.top = y + 'px';
    });
    drawConnections();
    savePositions();
}

function clearGraph() {
    if (!confirm('Remove all nodes from the graph?')) return;
    Object.values(graphNodes).forEach(n => n.element.remove());
    graphNodes = {};
    localStorage.removeItem(STORAGE_KEY);
    drawConnections();
    renderProjectList();
}

// CRUD
async function addRelation() {
    const source = document.getElementById('sourceProject').value;
    const target = document.getElementById('targetProject').value;
    const type = document.getElementById('relationType').value;
    const note = document.getElementById('relationNote').value;

    if (!source || !target || !type) { alert('Please fill in all required fields'); return; }
    if (source === target) { alert('Projects must be different'); return; }

    const result = await api.post('/api/relations', {source, target, type, note});
    if (result.error) { alert(result.error); return; }

    document.getElementById('sourceProject').value = '';
    document.getElementById('sourceProjectInput').value = '';
    document.getElementById('sourceProjectInput').classList.remove('has-value');
    document.getElementById('targetProject').value = '';
    document.getElementById('targetProjectInput').value = '';
    document.getElementById('targetProjectInput').classList.remove('has-value');
    document.getElementById('relationNote').value = '';
    loadData();
}

async function deleteRelation(id) {
    await api.del(`/api/relations/${id}`);
    loadData();
}

function showAddTypeModal() { document.getElementById('addTypeModal').classList.add('show'); }
function hideAddTypeModal() { document.getElementById('addTypeModal').classList.remove('show'); }

async function addRelationType() {
    const name = document.getElementById('newTypeName').value.trim();
    const icon = document.getElementById('newTypeIcon').value.trim() || '';
    const color = document.getElementById('newTypeColor').value;

    if (!name) { alert('Please enter a name'); return; }

    const id = name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    const result = await api.post('/api/relations/types', {id, name, icon, color});
    if (result.error) { alert(result.error); return; }

    hideAddTypeModal();
    document.getElementById('newTypeName').value = '';
    loadData();
}

// Tab switching
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab-btn[onclick*="${tab}"]`).classList.add('active');
    document.getElementById(tab + 'View').classList.add('active');

    if (tab === 'graph') {
        setTimeout(drawConnections, 100);
    }
}

// Init
loadData();
