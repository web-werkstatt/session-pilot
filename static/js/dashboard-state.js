// === DASHBOARD GLOBAL STATE ===
// Shared state variables used across all dashboard modules

/**
 * Renders an icon value as either a Lucide icon element or an emoji character.
 * Supports both legacy emoji data and new Lucide icon names.
 * @param {string} icon - Emoji character or Lucide icon name (e.g. "lightbulb")
 * @param {string} [cls] - Optional CSS class for the Lucide <i> element
 * @returns {string} HTML string
 */
function renderIcon(icon, cls) {
    if (!icon) return '';
    // If the string is short and contains non-ASCII (emoji), render as-is
    if (/[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\u{FE00}-\u{FEFF}]|[\u{2700}-\u{27BF}]|[\u{2300}-\u{23FF}]|[\u{200D}]|[\u{FE0F}]|[\u{E000}-\u{F8FF}]/u.test(icon)) {
        return icon;
    }
    // Otherwise treat as Lucide icon name
    var className = cls ? ' class="' + cls + '"' : '';
    return '<i data-lucide="' + icon + '"' + className + '></i>';
}

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
