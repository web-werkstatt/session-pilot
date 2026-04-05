var ACTIVE_PROJECT_STORAGE_KEY = 'active-project-context';

function setActiveProjectContext(projectName) {
    var value = String(projectName || '').trim();
    if (!value) return;
    try {
        localStorage.setItem(ACTIVE_PROJECT_STORAGE_KEY, value);
    } catch (e) {}
}

function getActiveProjectContext() {
    try {
        return localStorage.getItem(ACTIVE_PROJECT_STORAGE_KEY) || '';
    } catch (e) {
        return '';
    }
}

window.setActiveProjectContext = setActiveProjectContext;
window.getActiveProjectContext = getActiveProjectContext;
