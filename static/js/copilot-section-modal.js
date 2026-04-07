/* Copilot - Add Section Modal (extrahiert aus copilot_board.js)
 *
 * Wird nach copilot_board.js geladen. openAddSectionModal/createSection sind global
 * und nutzen _loadSections aus copilot_board.js sowie openModal/closeModal/_showToast aus base.js.
 */

function openAddSectionModal() {
    document.getElementById('newSectionTitle').value = '';
    document.getElementById('newSectionKind').value = 'section';
    document.getElementById('newSectionSummary').value = '';
    document.getElementById('newSectionSpecRef').value = '';
    openModal('addSectionModal');
    document.getElementById('newSectionTitle').focus();
}

function createSection() {
    var title = document.getElementById('newSectionTitle').value.trim();
    if (!title) { _showToast('Titel ist erforderlich', true); return; }

    var body = {
        title: title,
        kind: document.getElementById('newSectionKind').value,
        summary: document.getElementById('newSectionSummary').value.trim() || null,
        spec_ref: document.getElementById('newSectionSpecRef').value.trim() || null,
    };

    api.post('/api/plans/' + PLAN_ID + '/sections', body)
        .then(function() {
            closeModal('addSectionModal');
            _showToast('AI Task erstellt');
            _loadSections();
        })
        .catch(function(err) {
            _showToast('Fehler: ' + (err.message || 'Erstellen fehlgeschlagen'), true);
        });
}
