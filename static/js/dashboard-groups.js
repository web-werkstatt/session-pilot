// === DASHBOARD GROUPS ===
// Gruppen laden, rendern, erstellen, bearbeiten, loeschen

// Gruppen laden
function loadGroups() {
    return fetch('/api/groups')
        .then(r => r.json())
        .then(data => {
            groupsData = data;
            renderGroupFilterButtons();
            return data;
        })
        .catch(err => {
            console.error('Fehler beim Laden der Gruppen:', err);
            return { groups: [] };
        });
}

// Gruppen-Filter als Dropdown rendern
function renderGroupFilterButtons() {
    const select = document.getElementById('groupFilterSelect');
    if (!select) return;
    let html = '<option value="all">Alle Gruppen</option>';
    html += '<option value="priority">Prioritaet</option>';
    html += '<option value="none">Ungrouped</option>';

    groupsData.groups.forEach(group => {
        html += `<option value="${group.id}">${group.icon} ${group.name}</option>`;
    });

    select.innerHTML = html;
}

// Gruppen-Dropdown im Edit-Modal aktualisieren
function updateGroupDropdown(selectNewGroupId = null) {
    const select = document.getElementById('editGroup');
    const currentValue = select.value;
    let html = '<option value="">-- Keine --</option>';

    groupsData.groups.forEach(group => {
        html += `<option value="${group.id}">${group.icon} ${group.name}</option>`;
    });

    select.innerHTML = html;

    // Entweder neue Gruppe oder vorherigen Wert wiederherstellen
    if (selectNewGroupId) {
        select.value = selectNewGroupId;
    } else if (currentValue) {
        select.value = currentValue;
    }
}

// Inline-Formular für neue Gruppe ein-/ausblenden
function toggleInlineGroupForm() {
    const form = document.getElementById('inlineGroupForm');
    if (form.style.display === 'none') {
        form.style.display = 'block';
        document.getElementById('inlineGroupId').focus();
    } else {
        form.style.display = 'none';
        // Felder zurücksetzen
        document.getElementById('inlineGroupId').value = '';
        document.getElementById('inlineGroupName').value = '';
        document.getElementById('inlineGroupIcon').value = '📁';
        document.getElementById('inlineGroupColor').value = '#666666';
    }
}

// Neue Gruppe inline erstellen
function createInlineGroup() {
    let id = document.getElementById('inlineGroupId').value.trim().toLowerCase();
    id = id.replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    const name = document.getElementById('inlineGroupName').value.trim();
    const icon = document.getElementById('inlineGroupIcon').value;
    const color = document.getElementById('inlineGroupColor').value;

    if (!id || !name) {
        alert('Kurzname und Anzeigename sind erforderlich');
        return;
    }

    fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, icon, color, description: '' })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            // Gruppen neu laden und neue Gruppe auswählen
            loadGroups().then(() => {
                updateGroupDropdown(id);
                toggleInlineGroupForm();
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// Gruppen-Badge dynamisch generieren
function getGroupBadge(groupId) {
    if (!groupId) return '-';
    const group = groupsData.groups.find(g => g.id === groupId);
    if (group) {
        return `<span title="${group.name}" style="font-size:16px">${group.icon}</span>`;
    }
    return '-';
}

// Gruppen-Modal öffnen
function openGroupsModal() {
    document.getElementById('groupsModal').classList.add('show');
    renderGroupsList();
}

function closeGroupsModal() {
    document.getElementById('groupsModal').classList.remove('show');
}

// Gruppen-Liste im Modal rendern
function renderGroupsList() {
    const container = document.getElementById('groupsList');

    if (groupsData.groups.length === 0) {
        container.innerHTML = '<p style="color:#888;text-align:center">Keine Gruppen definiert</p>';
        return;
    }

    let html = '';
    groupsData.groups.forEach(group => {
        html += `
            <div class="group-item" data-group-id="${group.id}">
                <div class="group-color-bar" style="background:${group.color}"></div>
                <div class="group-icon-preview">${group.icon}</div>
                <div class="group-info">
                    <div class="group-name">${group.name}</div>
                    <div class="group-id">${group.id}</div>
                    ${group.description ? `<div class="group-desc">${group.description}</div>` : ''}
                </div>
                <div class="group-actions">
                    <button onclick="editGroup('${group.id}')">Bearbeiten</button>
                    <button class="btn-delete" onclick="deleteGroup('${group.id}')">Löschen</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Neue Gruppe erstellen
function createGroup() {
    // ID bereinigen: Kleinbuchstaben, Leerzeichen durch Unterstriche ersetzen, Sonderzeichen entfernen
    let id = document.getElementById('newGroupId').value.trim().toLowerCase();
    id = id.replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
    const name = document.getElementById('newGroupName').value.trim();
    const icon = document.getElementById('newGroupIcon').value.trim() || '📁';
    const color = document.getElementById('newGroupColor').value;
    const desc = document.getElementById('newGroupDesc').value.trim();

    if (!id || !name) {
        alert('ID und Name sind erforderlich');
        return;
    }

    fetch('/api/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, name, icon, color, description: desc })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            // Felder leeren
            document.getElementById('newGroupId').value = '';
            document.getElementById('newGroupName').value = '';
            document.getElementById('newGroupIcon').value = '';
            document.getElementById('newGroupColor').value = '#666666';
            document.getElementById('newGroupDesc').value = '';
            // Gruppen neu laden
            loadGroups().then(() => {
                renderGroupsList();
                updateGroupDropdown();
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// Gruppe bearbeiten
function editGroup(groupId) {
    const group = groupsData.groups.find(g => g.id === groupId);
    if (!group) return;

    const newName = prompt('Name:', group.name);
    if (newName === null) return;

    const newIcon = prompt('Icon (Emoji):', group.icon);
    if (newIcon === null) return;

    const newColor = prompt('Farbe (Hex):', group.color);
    if (newColor === null) return;

    const newDesc = prompt('Beschreibung:', group.description || '');
    if (newDesc === null) return;

    fetch(`/api/groups/${groupId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: newName,
            icon: newIcon,
            color: newColor,
            description: newDesc
        })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            loadGroups().then(() => {
                renderGroupsList();
                updateGroupDropdown();
                loadData(); // Tabelle aktualisieren
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}

// Gruppe löschen
function deleteGroup(groupId) {
    const group = groupsData.groups.find(g => g.id === groupId);
    if (!group) return;

    if (!confirm(`Möchten Sie die Gruppe "${group.name}" wirklich löschen?\n\nProjekte mit dieser Gruppe werden auf "Keine Gruppe" gesetzt.`)) {
        return;
    }

    fetch(`/api/groups/${groupId}`, { method: 'DELETE' })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            loadGroups().then(() => {
                renderGroupsList();
                updateGroupDropdown();
                loadData(); // Tabelle aktualisieren
            });
        } else {
            alert('Fehler: ' + result.error);
        }
    })
    .catch(err => alert('Fehler: ' + err));
}
