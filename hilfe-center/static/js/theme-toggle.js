(function() {
    'use strict';
    const STORAGE_KEY = 'cms-help-theme';

    function getStoredTheme() {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) return stored;
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) return 'light';
        return 'dark';
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-bs-theme', theme);
        localStorage.setItem(STORAGE_KEY, theme);
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-bs-theme') || 'dark';
        applyTheme(current === 'dark' ? 'light' : 'dark');
    }

    applyTheme(getStoredTheme());

    function init() {
        if (!document.body) { setTimeout(init, 50); return; }
        if (document.querySelector('.theme-toggle')) return;
        const btn = document.createElement('button');
        btn.className = 'theme-toggle';
        btn.setAttribute('aria-label', 'Theme umschalten');
        btn.innerHTML = '<i class="bi bi-moon-fill"></i><i class="bi bi-sun-fill"></i><span class="theme-label-dark">Light Mode</span><span class="theme-label-light">Dark Mode</span>';
        btn.addEventListener('click', toggleTheme);
        document.body.appendChild(btn);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();

    window.CMSTheme = { toggle: toggleTheme, set: applyTheme, get: function() { return document.documentElement.getAttribute('data-bs-theme') || 'dark'; } };
})();
