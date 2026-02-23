/**
 * Chapter Email Inbox JavaScript (Issue #3831)
 *
 * Handles AJAX operations for the inbox UI:
 * - Mark thread as read
 * - Update thread status/assignment
 * - Avatars, relative timestamps
 * - Quick actions (assign/close from list view)
 */

var InboxApp = (function() {
    'use strict';

    var csrfToken = $j.cookie('esp_csrftoken');

    // ── Avatar colors (deterministic by email hash) ──
    var AVATAR_COLORS = [
        '#e74c3c', '#3498db', '#2ecc71', '#9b59b6',
        '#f39c12', '#1abc9c', '#e67e22', '#34495e'
    ];

    function hashCode(str) {
        var hash = 0;
        for (var i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash) + str.charCodeAt(i);
            hash |= 0;
        }
        return Math.abs(hash);
    }

    function getAvatarColor(email) {
        return AVATAR_COLORS[hashCode(email) % AVATAR_COLORS.length];
    }

    function getInitials(email) {
        if (!email) return '?';
        var local = email.split('@')[0] || '';
        if (!local) return '?';
        var parts = local.split(/[._-]/).filter(function(p) { return p.length > 0; });
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        var alphanum = local.replace(/[^a-zA-Z0-9]/g, '');
        return (alphanum.substring(0, 2) || '??').toUpperCase();
    }

    function renderAvatars() {
        $j('.inbox-avatar[data-email]').each(function() {
            var el = $j(this);
            var email = el.data('email');
            el.css('background-color', getAvatarColor(email));
            el.text(getInitials(email));
        });
    }

    // ── Relative Timestamps ──
    function relativeTime(dateStr) {
        if (!dateStr) return '';
        var date = new Date(dateStr);
        var now = new Date();
        var diff = Math.floor((now - date) / 1000);

        if (diff < 60) return 'Just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        if (diff < 172800) return 'Yesterday';
        if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }

    function renderRelativeDates() {
        $j('[data-timestamp]').each(function() {
            var el = $j(this);
            var ts = el.data('timestamp');
            el.text(relativeTime(ts));
            el.attr('title', new Date(ts).toLocaleString());
        });
    }

    // ── AJAX Helpers ──
    function ajaxPost(url, data, onSuccess, onError) {
        $j.ajax({
            url: url,
            type: 'POST',
            data: data,
            timeout: 30000,
            beforeSend: function(xhr) {
                xhr.setRequestHeader('X-CSRFToken', csrfToken);
            },
            success: onSuccess,
            error: function(xhr, textStatus) {
                var msg = textStatus === 'timeout' ? 'Request timed out' : 'Request failed';
                try { msg = JSON.parse(xhr.responseText).message || msg; } catch(e) {}
                if (onError) onError(msg);
            }
        });
    }

    function showFeedback(selector, text, isError) {
        var el = $j(selector);
        el.text(text).css({
            'opacity': 1,
            'color': isError ? '#dc2626' : '#16a34a'
        });
        setTimeout(function() {
            el.css('opacity', 0);
        }, isError ? 3000 : 2000);
    }

    // ── Thread Read ──
    function markRead(threadId) {
        ajaxPost('/manage/inbox/thread/' + threadId + '/mark-read/', {});
    }

    // ── Thread Update ──
    function updateThread(threadId, data) {
        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/update/',
            data,
            function() { showFeedback('#thread-update-feedback', 'Updated!', false); },
            function() { showFeedback('#thread-update-feedback', 'Update failed', true); }
        );
    }

    // ── Quick Actions (list view) ──
    function quickAssignMe(threadId) {
        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/update/',
            { assigned_to: 'self', status: 'in_progress' },
            function() { location.reload(); },
            function(msg) { alert('Failed: ' + msg); }
        );
    }

    function quickClose(threadId) {
        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/update/',
            { status: 'closed' },
            function() { location.reload(); },
            function(msg) { alert('Failed: ' + msg); }
        );
    }

    // ── Initialization ──
    $j(function() {
        renderAvatars();
        renderRelativeDates();

        // Refresh relative timestamps every 60 seconds
        setInterval(renderRelativeDates, 60000);

        // Thread detail: status/assignee change
        $j('#thread-status-select').on('change', function() {
            var threadId = getThreadId();
            if (threadId) updateThread(threadId, { status: $j(this).val() });
        });
        $j('#thread-assignee-select').on('change', function() {
            var threadId = getThreadId();
            if (threadId) updateThread(threadId, { assigned_to: $j(this).val() });
        });
    });

    function getThreadId() {
        var match = window.location.pathname.match(/\/manage\/inbox\/thread\/(\d+)/);
        return match ? match[1] : null;
    }

    return {
        markRead: markRead,
        updateThread: updateThread,
        quickAssignMe: quickAssignMe,
        quickClose: quickClose,
        renderAvatars: renderAvatars,
        renderRelativeDates: renderRelativeDates,
        getAvatarColor: getAvatarColor,
        getInitials: getInitials
    };
})();
