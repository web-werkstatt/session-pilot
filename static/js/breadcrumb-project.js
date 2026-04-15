/*
 * Phase 7 (2026-04-14): Globale Breadcrumb-Ergaenzung.
 * Wenn die URL einen ?project=<name>-Parameter traegt, wird der Projektname
 * als klickbarer Link zwischen "Workspace" und dem aktiven Breadcrumb-Segment
 * eingeblendet: "Workspace / <Projekt> / <Seite>".
 *
 * Skip-Regel: Wenn der aktive Breadcrumb den Projektnamen schon enthaelt
 * (z.B. copilot_board.html oder project_detail.html), wird nichts injiziert.
 */
(function () {
    function init() {
        var params = new URLSearchParams(window.location.search);
        var project = (params.get('project') || '').trim();
        if (!project) return;

        var bcActive = document.querySelector('.breadcrumb .bc-active');
        if (!bcActive) return;

        // Schon drin? (Duplikat vermeiden)
        if (bcActive.textContent.indexOf(project) !== -1) return;

        var breadcrumb = bcActive.parentNode;

        var link = document.createElement('a');
        link.href = '/project/' + encodeURIComponent(project);
        link.textContent = project;
        link.className = 'bc-link bc-project-injected';

        var sep = document.createElement('span');
        sep.className = 'bc-sep';
        sep.textContent = '/';

        breadcrumb.insertBefore(link, bcActive);
        breadcrumb.insertBefore(document.createTextNode(' '), bcActive);
        breadcrumb.insertBefore(sep, bcActive);
        breadcrumb.insertBefore(document.createTextNode(' '), bcActive);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
