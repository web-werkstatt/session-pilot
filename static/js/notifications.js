/**
 * Notification System: Badge-Polling, Panel, Read/Dismiss
 */

var notificationPollTimer = null;

// Badge-Polling alle 15 Sekunden
function startNotificationPolling() {
    pollNotificationCount();
    notificationPollTimer = setInterval(pollNotificationCount, 15000);
}

function pollNotificationCount() {
    fetch('/api/notifications/count')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var badge = document.getElementById('notificationBadge');
            if (!badge) return;
            if (data.unread > 0) {
                badge.textContent = data.unread > 99 ? '99+' : data.unread;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        })
        .catch(function() {});
}

function toggleNotificationPanel() {
    var panel = document.getElementById('notificationPanel');
    if (!panel) return;
    if (panel.classList.contains('show')) {
        panel.classList.remove('show');
    } else {
        panel.classList.add('show');
        loadNotifications();
    }
}

function loadNotifications() {
    fetch('/api/notifications?limit=50')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            renderNotifications(data.notifications || []);
        });
}

function renderNotifications(notifications) {
    var list = document.getElementById('notificationList');
    if (!list) return;

    if (!notifications.length) {
        list.innerHTML = '<div class="notification-empty">Keine Benachrichtigungen</div>';
        return;
    }

    var icons = {
        container_down: '&#9940;',
        container_unhealthy: '&#9888;',
        new_commit: '&#128229;',
        sync_conflict: '&#128260;',
        new_project: '&#128193;',
    };

    var html = '';
    notifications.forEach(function(n) {
        var unread = n.read ? '' : ' unread';
        var icon = icons[n.type] || '&#128276;';
        var time = formatTimeAgo(n.created_at);

        html += '<div class="notification-item severity-' + n.severity + unread + '" data-id="' + n.id + '" onclick="onNotificationClick(\'' + n.id + '\', \'' + (n.project || '') + '\')">';
        html += '<span class="notification-icon">' + icon + '</span>';
        html += '<div class="notification-body">';
        html += '<div class="notification-title">' + escapeNotifHtml(n.title) + '</div>';
        if (n.message) {
            html += '<div class="notification-message">' + escapeNotifHtml(n.message) + '</div>';
        }
        html += '<div class="notification-time">' + time + '</div>';
        html += '</div>';
        html += '<button class="notification-dismiss" onclick="event.stopPropagation();dismissNotification(\'' + n.id + '\')" title="Entfernen">&#10005;</button>';
        html += '</div>';
    });
    list.innerHTML = html;
}

function onNotificationClick(id, project) {
    // Als gelesen markieren
    fetch('/api/notifications/' + id + '/read', {method: 'POST'});

    // Zum Projekt navigieren (falls vorhanden)
    if (project) {
        location.href = '/project/' + encodeURIComponent(project);
    } else {
        // Item visuell als gelesen markieren
        var item = document.querySelector('[data-id="' + id + '"]');
        if (item) item.classList.remove('unread');
        pollNotificationCount();
    }
}

function dismissNotification(id) {
    fetch('/api/notifications/' + id, {method: 'DELETE'})
        .then(function() {
            var item = document.querySelector('[data-id="' + id + '"]');
            if (item) item.remove();
            pollNotificationCount();
        });
}

function markAllNotificationsRead() {
    fetch('/api/notifications/read-all', {method: 'POST'})
        .then(function() {
            document.querySelectorAll('.notification-item.unread').forEach(function(el) {
                el.classList.remove('unread');
            });
            pollNotificationCount();
        });
}

function formatTimeAgo(isoStr) {
    if (!isoStr) return '';
    var date = new Date(isoStr);
    var now = new Date();
    var diff = Math.floor((now - date) / 1000);
    if (diff < 60) return 'Gerade eben';
    if (diff < 3600) return Math.floor(diff / 60) + ' Min.';
    if (diff < 86400) return Math.floor(diff / 3600) + ' Std.';
    return Math.floor(diff / 86400) + ' Tage';
}

function escapeNotifHtml(text) {
    var div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

// Panel schliessen bei Klick ausserhalb
document.addEventListener('click', function(e) {
    var panel = document.getElementById('notificationPanel');
    var bell = document.getElementById('notificationBell');
    if (panel && panel.classList.contains('show') && !panel.contains(e.target) && !bell.contains(e.target)) {
        panel.classList.remove('show');
    }
});

// Polling starten wenn DOM bereit
document.addEventListener('DOMContentLoaded', startNotificationPolling);
