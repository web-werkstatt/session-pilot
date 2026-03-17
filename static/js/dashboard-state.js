// === DASHBOARD GLOBAL STATE ===
// Shared state variables used across all dashboard modules

let firstLoad = true;
let allRelations = [];
let relationTypes = [];
let groupsData = { groups: [] };
let favorites = [];
let showArchived = false;
let allProjectsData = [];
let currentGroupFilter = 'all';
let currentSearchTerm = '';
let searchDebounceTimer = null;
let currentViewMode = 'priority';  // 'priority' oder 'groups'
let currentSortCol = null;
let currentSortDir = null;
let currentSort = { field: 'activity', dir: 'desc' };
let currentNewsHash = '';
let currentEditProject = null;
let editRelationSearchTimeout = null;
let editRelationAbortController = null;
