// === DASHBOARD FILTERS ===
// View-Mode, Group-Filter, Search, Filter/Sort logic, Sorting

// View-Mode wechseln
function setViewMode(mode) {
    currentViewMode = mode;
    document.getElementById('viewPriorityBtn').classList.toggle('active', mode === 'priority');
    document.getElementById('viewGroupBtn').classList.toggle('active', mode === 'groups');
    // Daten neu rendern
    if (allProjectsData.projects) {
        renderProjectsTable(allProjectsData);
    }
}

function setGroupFilter(filter, btn) {
    currentGroupFilter = filter;
    document.querySelectorAll('#filterBar .filter-btn').forEach(b => b.classList.remove('active'));
    // btn kann über event.target oder als Parameter kommen
    const targetBtn = btn || event.target;
    if (targetBtn) targetBtn.classList.add('active');
    applyFiltersAndSort();
}

// Live-Suche mit Debounce
function handleSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        const input = document.getElementById('searchInput');
        const clearBtn = document.getElementById('searchClear');
        currentSearchTerm = input.value.trim().toLowerCase();

        // X-Button anzeigen/verstecken
        if (currentSearchTerm) {
            clearBtn.classList.add('show');
        } else {
            clearBtn.classList.remove('show');
        }

        applyFiltersAndSort();
    }, 150); // 150ms Debounce für flüssiges Tippen
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('searchClear').classList.remove('show');
    document.getElementById('searchResults').innerHTML = '';
    currentSearchTerm = '';
    applyFiltersAndSort();
}

function applyFiltersAndSort() {
    const tbody = document.getElementById('tableBody');
    const rows = tbody.querySelectorAll('tr:not(.section-header)');
    let visibleCount = 0;
    let totalCount = rows.length;

    rows.forEach(row => {
        const group = row.dataset.group || '';
        const priority = row.dataset.priority || '';
        const searchText = row.dataset.searchtext || '';
        const isArchived = row.dataset.archived === '1';
        let visible = true;

        // Archiv-Filter: standardmaessig ausblenden
        if (isArchived && !showArchived) {
            visible = false;
        }

        // Gruppenfilter
        if (visible && currentGroupFilter !== 'all') {
            if (currentGroupFilter === 'priority') {
                if (!priority) visible = false;
            } else if (currentGroupFilter === 'none') {
                if (group) visible = false;
            } else if (group !== currentGroupFilter) {
                visible = false;
            }
        }

        // Suchfilter
        if (visible && currentSearchTerm) {
            visible = searchText.includes(currentSearchTerm);
        }

        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
    });

    // Suchergebnis-Anzeige aktualisieren
    const resultsEl = document.getElementById('searchResults');
    if (currentSearchTerm) {
        resultsEl.innerHTML = `<span class="count">${visibleCount}</span> of ${totalCount} projects`;
    } else {
        resultsEl.innerHTML = '';
    }

    // Section-Header ausblenden wenn keine sichtbaren Zeilen darunter
    updateSectionHeaders();
}

function updateSectionHeaders() {
    const tbody = document.getElementById('tableBody');
    const headers = tbody.querySelectorAll('tr.section-header');

    headers.forEach(header => {
        let hasVisibleRows = false;
        let nextRow = header.nextElementSibling;

        while (nextRow && !nextRow.classList.contains('section-header')) {
            if (nextRow.style.display !== 'none') {
                hasVisibleRows = true;
                break;
            }
            nextRow = nextRow.nextElementSibling;
        }

        header.style.display = hasVisibleRows ? '' : 'none';
    });
}

// === SORTIER FUNKTIONEN ===
function initSorting() {
    document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', function() {
            const field = this.dataset.sort;
            if (currentSort.field === field) {
                currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.dir = 'asc';
            }
            document.querySelectorAll('th.sortable').forEach(h => h.classList.remove('asc', 'desc'));
            this.classList.add(currentSort.dir);
            loadData();
        });
    });
}
