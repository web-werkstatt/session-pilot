/**
 * Notification System: Badge-Polling, Panel, Read/Dismiss
 */

var notificationPollTimer = null;

// Badge-Polling alle 15 Sekunden
function startNotificationPolling() {
    pollNotificationCount();
    pollPolicyPendingCount();
    notificationPollTimer = setInterval(function() {
        pollNotificationCount();
        pollPolicyPendingCount();
    }, 15000);
}

function pollNotificationCount() {
    api.get('/api/notifications/count')
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

function pollPolicyPendingCount() {
    var badge = document.getElementById('policyPendingBadge');
    if (!badge) return;
    api.get('/api/policies/suggestions?status=pending')
        .then(function(data) {
            var count = (data.suggestions || []).length;
            if (count > 0) {
                badge.textContent = count;
                badge.style.display = 'inline-flex';
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
    api.get('/api/notifications?limit=50')
        .then(function(data) {
            renderNotifications(data.notifications || []);
        });
}

function renderNotifications(notifications) {
    var list = document.getElementById('notificationList');
    if (!list) return;

    if (!notifications.length) {
        list.innerHTML = '<div class="notification-empty">No notifications</div>';
        return;
    }

    var icons = {
        container_down: '<i data-lucide="circle-x" class="icon"></i>',
        container_unhealthy: '<i data-lucide="alert-triangle" class="icon"></i>',
        new_commit: '<i data-lucide="git-commit" class="icon"></i>',
        sync_conflict: '<i data-lucide="git-pull-request" class="icon"></i>',
        new_project: '<i data-lucide="folder-plus" class="icon"></i>',
    };

    var html = '';
    notifications.forEach(function(n) {
        var unread = n.read ? '' : ' unread';
        var icon = icons[n.type] || '<i data-lucide="bell" class="icon"></i>';
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
        html += '<button class="notification-dismiss" onclick="event.stopPropagation();dismissNotification(\'' + n.id + '\')" title="Remove">&#10005;</button>';
        html += '</div>';
    });
    list.innerHTML = html;
    if (typeof lucide !== 'undefined') lucide.createIcons();
}

function onNotificationClick(id, project) {
    // Als gelesen markieren
    api.post('/api/notifications/' + id + '/read');

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
    api.del('/api/notifications/' + id)
        .then(function() {
            var item = document.querySelector('[data-id="' + id + '"]');
            if (item) item.remove();
            pollNotificationCount();
        });
}

function markAllNotificationsRead() {
    api.post('/api/notifications/read-all')
        .then(function() {
            document.querySelectorAll('.notification-item.unread').forEach(function(el) {
                el.classList.remove('unread');
            });
            pollNotificationCount();
        });
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
