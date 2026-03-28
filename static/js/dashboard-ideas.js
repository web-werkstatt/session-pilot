// === DASHBOARD IDEAS / NOTIZEN ===
// Ideen laden, erstellen, bearbeiten, loeschen, filtern

let ideasData = { ideas: [], categories: [] };
let currentEditIdea = null;

async function loadIdeas() {
    const resp = await fetch('/api/ideas');
    ideasData = await resp.json();
    renderIdeasList();
}

function openIdeasModal() {
    openModal('ideasModal');
    loadIdeas();
}

function closeIdeasModal() {
    closeModal('ideasModal');
    currentEditIdea = null;
    resetIdeaForm();
}

function resetIdeaForm() {
    document.getElementById('ideaTitle').value = '';
    document.getElementById('ideaContent').value = '';
    document.getElementById('ideaCategory').value = 'note';
    document.getElementById('ideaPriority').value = 'normal';
    document.getElementById('ideaProject').value = '';
    document.getElementById('ideaFormTitle').textContent = 'Neue Idee';
    document.getElementById('ideaSaveBtn').textContent = 'Speichern';
    currentEditIdea = null;
}

function renderIdeasList() {
    const container = document.getElementById('ideasList');
    const filterCategory = document.getElementById('ideasFilterCategory').value;
    const filterStatus = document.getElementById('ideasFilterStatus').value;

    let filtered = ideasData.ideas;
    if (filterCategory) {
        filtered = filtered.filter(i => i.category === filterCategory);
    }
    if (filterStatus) {
        filtered = filtered.filter(i => i.status === filterStatus);
    }

    if (filtered.length === 0) {
        container.innerHTML = '<div style="text-align:center;color:#666;padding:40px;">Keine Ideen vorhanden</div>';
        return;
    }

    container.innerHTML = filtered.map(idea => {
        const cat = ideasData.categories.find(c => c.id === idea.category) || {icon: '<i data-lucide="file-text" class="icon"></i>', color: '#666'};
        const priorityIcon = idea.priority === 'high' ? '<i data-lucide="circle" class="icon-priority-high"></i>' : idea.priority === 'low' ? '<i data-lucide="circle" class="icon-priority-low"></i>' : '';
        const statusClass = idea.status === 'done' ? 'idea-done' : idea.status === 'archived' ? 'idea-archived' : '';
        const date = new Date(idea.created).toLocaleDateString('de-DE');
        return `
            <div class="idea-card ${statusClass}" onclick="editIdea('${idea.id}')">
                <div class="idea-header">
                    <span class="idea-cat" style="background:${cat.color}30;color:${cat.color}">${renderIcon(cat.icon)}</span>
                    <span class="idea-title">${priorityIcon} ${idea.title}</span>
                    <span class="idea-date">${date}</span>
                </div>
                ${idea.content ? `<div class="idea-content">${idea.content.substring(0, 150)}${idea.content.length > 150 ? '...' : ''}</div>` : ''}
                ${idea.project ? `<div class="idea-project"><i data-lucide="folder" class="icon"></i> ${idea.project}</div>` : ''}
                <div class="idea-actions">
                    <button class="idea-status-btn" onclick="event.stopPropagation();toggleIdeaStatus('${idea.id}','${idea.status}')">${idea.status === 'done' ? '<i data-lucide="rotate-ccw" class="icon"></i> Öffnen' : '<i data-lucide="check" class="icon"></i> Erledigt'}</button>
                    <button class="idea-delete-btn" onclick="event.stopPropagation();deleteIdea('${idea.id}')"><i data-lucide="trash-2" class="icon"></i></button>
                </div>
            </div>
        `;
    }).join('');
    if (typeof lucide !== 'undefined') lucide.createIcons();

    // Kategorien für Filter
    document.getElementById('ideasFilterCategory').innerHTML = '<option value="">Alle Kategorien</option>' +
        ideasData.categories.map(c => `<option value="${c.id}">${renderIcon(c.icon)} ${c.name}</option>`).join('');

    // Kategorien für Form
    document.getElementById('ideaCategory').innerHTML = ideasData.categories.map(c =>
        `<option value="${c.id}">${renderIcon(c.icon)} ${c.name}</option>`
    ).join('');

    // Projekte für Form (aus allProjectsData)
    if (allProjectsData && allProjectsData.projects) {
        const projectOptions = allProjectsData.projects
            .filter(p => p.project_type !== 'subproject')
            .map(p => `<option value="${p.name}">${p.name}</option>`)
            .join('');
        document.getElementById('ideaProject').innerHTML = '<option value="">Kein Projekt</option>' + projectOptions;
    }
}

function editIdea(ideaId) {
    const idea = ideasData.ideas.find(i => i.id === ideaId);
    if (!idea) return;

    currentEditIdea = ideaId;
    document.getElementById('ideaTitle').value = idea.title;
    document.getElementById('ideaContent').value = idea.content || '';
    document.getElementById('ideaCategory').value = idea.category;
    document.getElementById('ideaPriority').value = idea.priority;
    document.getElementById('ideaProject').value = idea.project || '';
    document.getElementById('ideaFormTitle').textContent = 'Idee bearbeiten';
    document.getElementById('ideaSaveBtn').textContent = 'Aktualisieren';
}

async function saveIdea() {
    const title = document.getElementById('ideaTitle').value.trim();
    const content = document.getElementById('ideaContent').value.trim();
    const category = document.getElementById('ideaCategory').value;
    const priority = document.getElementById('ideaPriority').value;
    const project = document.getElementById('ideaProject').value || null;

    if (!title) {
        alert('Bitte einen Titel eingeben');
        return;
    }

    const data = { title, content, category, priority, project };

    if (currentEditIdea) {
        // Update
        await fetch(`/api/ideas/${currentEditIdea}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    } else {
        // Create
        await fetch('/api/ideas', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
    }

    resetIdeaForm();
    loadIdeas();
}

async function deleteIdea(ideaId) {
    if (!confirm('Idee wirklich löschen?')) return;
    await fetch(`/api/ideas/${ideaId}`, { method: 'DELETE' });
    loadIdeas();
}

async function toggleIdeaStatus(ideaId, currentStatus) {
    const newStatus = currentStatus === 'done' ? 'open' : 'done';
    await fetch(`/api/ideas/${ideaId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ status: newStatus })
    });
    loadIdeas();
}

function filterIdeas() {
    renderIdeasList();
}
