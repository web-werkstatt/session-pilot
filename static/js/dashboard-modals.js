// === DASHBOARD MODALS ===
// Edit modal, relations tab, milestones, keyboard shortcuts, dropdown close handler

function openEditModal(projectName) {
    currentEditProject = projectName;
    document.getElementById('editProjectName').textContent = projectName;
    openModal('editModal');

    // Gruppen-Dropdown aktualisieren
    updateGroupDropdown();

    // Relation Types laden (falls noch nicht geladen)
    if (relationTypes.length === 0) {
        loadRelationTypes();
    }

    // Tab auf Allgemein setzen
    switchEditTab('general');

    api.get(`/api/project/${encodeURIComponent(projectName)}`)
        .then(data => {
            document.getElementById('editDescription').value = data.description || '';
            document.getElementById('editGroup').value = data.group || '';
            document.getElementById('editPriority').value = data.priority || '';
            document.getElementById('editDeadline').value = data.deadline || '';
            document.getElementById('editProgress').value = data.progress !== null ? data.progress : '';

            const milestoneList = document.getElementById('milestoneList');
            milestoneList.innerHTML = '';
            if (data.milestones && data.milestones.length > 0) {
                data.milestones.forEach((m, i) => {
                    addMilestoneRow(m.name, m.done, i);
                });
            }
        })
        .catch(err => {
            console.error('Error loading:', err);
        });
}

function closeEditModal() {
    closeModal('editModal');
    currentEditProject = null;
    // Inline-Gruppen-Formular zurücksetzen
    const inlineForm = document.getElementById('inlineGroupForm');
    if (inlineForm) {
        inlineForm.style.display = 'none';
        document.getElementById('inlineGroupId').value = '';
        document.getElementById('inlineGroupName').value = '';
        document.getElementById('inlineGroupIcon').value = '';
        document.getElementById('inlineGroupColor').value = '#666666';
    }
    // Relations-Tab zurücksetzen
    switchEditTab('general');
    document.getElementById('editRelationProject').value = '';
    document.getElementById('editRelationNote').value = '';
    document.getElementById('editRelationDropdown').innerHTML = '';
    document.getElementById('editRelationDropdown').style.display = 'none';
}

// === RELATIONS TAB FUNKTIONEN ===

function switchEditTab(tab) {
    document.querySelectorAll('.modal-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.edit-tab-content').forEach(content => content.classList.remove('active'));

    if (tab === 'general') {
        document.querySelector('.modal-tab:first-child').classList.add('active');
        document.getElementById('editTabGeneral').classList.add('active');
    } else {
        document.querySelector('.modal-tab:last-child').classList.add('active');
        document.getElementById('editTabRelations').classList.add('active');
        loadProjectRelations();
    }
}

async function loadRelationTypes() {
    relationTypes = await api.get('/api/relations/types');
    const select = document.getElementById('editRelationType');
    select.innerHTML = relationTypes.map(t =>
        `<option value="${t.id}">${renderIcon(t.icon)} ${t.name}</option>`
    ).join('');
}

async function loadProjectRelations() {
    if (!currentEditProject) return;

    const data = await api.get(`/api/project/${encodeURIComponent(currentEditProject)}/relations`);

    const outgoingDiv = document.getElementById('outgoingRelations');
    const incomingDiv = document.getElementById('incomingRelations');

    if (data.outgoing.length === 0) {
        outgoingDiv.innerHTML = '<div style="color:#666;font-style:italic">No outgoing relations</div>';
    } else {
        outgoingDiv.innerHTML = data.outgoing.map(rel => {
            const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: 'link', name: rel.type, color: '#888'};
            return `
                <div class="relation-item" style="border-left:3px solid ${typeInfo.color}">
                    <span class="relation-type">${renderIcon(typeInfo.icon)} ${typeInfo.name}</span>
                    <span class="relation-target">→ ${rel.target}</span>
                    ${rel.note ? `<span class="relation-note">(${rel.note})</span>` : ''}
                    <button class="btn-remove" onclick="deleteProjectRelation('${rel.id}')" title="Delete">×</button>
                </div>
            `;
        }).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    if (data.incoming.length === 0) {
        incomingDiv.innerHTML = '<div style="color:#666;font-style:italic">No incoming relations</div>';
    } else {
        incomingDiv.innerHTML = data.incoming.map(rel => {
            const typeInfo = relationTypes.find(t => t.id === rel.type) || {icon: 'link', name: rel.type, color: '#888'};
            return `
                <div class="relation-item" style="border-left:3px solid ${typeInfo.color}">
                    <span class="relation-type">${renderIcon(typeInfo.icon)} ${typeInfo.name}</span>
                    <span class="relation-target">← ${rel.source}</span>
                    ${rel.note ? `<span class="relation-note">(${rel.note})</span>` : ''}
                    <button class="btn-remove" onclick="deleteProjectRelation('${rel.id}')" title="Delete">×</button>
                </div>
            `;
        }).join('');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }

    // Render Lucide Icons after DOM update
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function updateRelationForm() {
    const direction = document.querySelector('input[name="relationDirection"]:checked').value;
    document.getElementById('relationTargetLabel').textContent =
        direction === 'outgoing' ? 'Target Project' : 'Source Project';
}

function onEditRelationSearch() {
    clearTimeout(editRelationSearchTimeout);
    if (editRelationAbortController) editRelationAbortController.abort();

    const query = document.getElementById('editRelationProject').value.trim();
    const dropdown = document.getElementById('editRelationDropdown');

    if (query.length < 1) {
        dropdown.style.display = 'none';
        return;
    }

    editRelationSearchTimeout = setTimeout(async () => {
        editRelationAbortController = new AbortController();
        try {
            const results = await api.request(`/api/projects/search?q=${encodeURIComponent(query)}&limit=10`, {
                signal: editRelationAbortController.signal
            });

            // Aktuelles Projekt aus der Liste entfernen
            const filtered = results.filter(p => p.name !== currentEditProject);

            if (filtered.length === 0) {
                dropdown.innerHTML = '<div class="dropdown-item" style="color:#888">No results</div>';
            } else {
                dropdown.innerHTML = filtered.map(p => `
                    <div class="dropdown-item" onclick="selectEditRelationProject('${p.name}')">
                        <strong>${p.name}</strong>
                        ${p.description ? `<small style="color:#888;margin-left:8px">${p.description}</small>` : ''}
                    </div>
                `).join('');
            }
            dropdown.style.display = 'block';
        } catch (e) {
            if (e.name !== 'AbortError') console.error(e);
        }
    }, 200);
}

function selectEditRelationProject(name) {
    document.getElementById('editRelationProject').value = name;
    document.getElementById('editRelationDropdown').style.display = 'none';
}

async function addProjectRelation() {
    const targetProject = document.getElementById('editRelationProject').value.trim();
    const relationType = document.getElementById('editRelationType').value;
    const note = document.getElementById('editRelationNote').value.trim();
    const direction = document.querySelector('input[name="relationDirection"]:checked').value;

    if (!targetProject) {
        alert('Please select a project');
        return;
    }

    const source = direction === 'outgoing' ? currentEditProject : targetProject;
    const target = direction === 'outgoing' ? targetProject : currentEditProject;

    try {
        await api.post('/api/relations', { source, target, type: relationType, note });
        document.getElementById('editRelationProject').value = '';
        document.getElementById('editRelationNote').value = '';
        loadProjectRelations();
        loadData();
    } catch (err) {
        alert('Error: ' + (err.message || 'Unknown error'));
    }
}

async function deleteProjectRelation(id) {
    if (!confirm('Really delete this relation?')) return;

    await api.del(`/api/relations/${id}`);
    loadProjectRelations();
    loadData();
}

// Dropdown schließen bei Klick außerhalb
document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('editRelationDropdown');
    const input = document.getElementById('editRelationProject');
    if (dropdown && !dropdown.contains(e.target) && e.target !== input) {
        dropdown.style.display = 'none';
    }
});

function addMilestone() {
    const milestoneList = document.getElementById('milestoneList');
    const idx = milestoneList.children.length;
    addMilestoneRow('', false, idx);
}

function addMilestoneRow(name, done, idx) {
    const milestoneList = document.getElementById('milestoneList');
    const div = document.createElement('div');
    div.className = 'milestone-item';
    div.innerHTML = `
        <input type="checkbox" ${done ? 'checked' : ''} data-idx="${idx}">
        <input type="text" value="${name}" placeholder="Milestone name" data-idx="${idx}">
        <button type="button" class="btn-remove" onclick="this.parentElement.remove()">×</button>
    `;
    milestoneList.appendChild(div);
}

function removeMilestone(btn) {
    btn.parentElement.remove();
}

// Edit form submit handler
document.getElementById('editForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const milestones = [];
    document.querySelectorAll('#milestoneList .milestone-item').forEach(item => {
        const checkbox = item.querySelector('input[type="checkbox"]');
        const textInput = item.querySelector('input[type="text"]');
        if (textInput.value.trim()) {
            milestones.push({
                name: textInput.value.trim(),
                done: checkbox.checked
            });
        }
    });

    const data = {
        name: currentEditProject,
        description: document.getElementById('editDescription').value,
        group: document.getElementById('editGroup').value || null,
        priority: document.getElementById('editPriority').value || null,
        deadline: document.getElementById('editDeadline').value || null,
        progress: document.getElementById('editProgress').value ? parseInt(document.getElementById('editProgress').value) : null,
        milestones: milestones
    };

    api.post('/api/project/save', data)
    .then(result => {
        if (result.success) {
            closeEditModal();
            loadData();
        } else {
            alert('Error: ' + result.error);
        }
    })
    .catch(err => {
        alert('Error saving: ' + err);
    });
});

// Escape-Fallback: Suche leeren wenn kein Modal offen
document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && _modalStack.length === 0 && typeof currentSearchTerm !== 'undefined' && currentSearchTerm) {
        clearSearch();
    }
});
