/**
 * Chapter Email Inbox JavaScript (Issue #3831)
 *
 * Handles all AJAX operations for the inbox UI:
 * - Mark thread as read
 * - Update thread status/assignment
 * - Avatars, relative timestamps
 * - Internal notes (add/delete)
 * - Labels (add/remove)
 * - Canned responses
 * - Bulk actions
 * - Export / Forward
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
        // Try splitting on dots, underscores, hyphens — filter empty parts
        var parts = local.split(/[._-]/).filter(function(p) { return p.length > 0; });
        if (parts.length >= 2) {
            return (parts[0][0] + parts[1][0]).toUpperCase();
        }
        // Single part or no valid split — take first 2 alphanumeric chars
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
            timeout: 30000,  // 30s timeout to prevent infinite spinners
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

    // ── Notes ──
    function addNote(threadId) {
        var textarea = $j('#inbox-note-text');
        var text = textarea.val().trim();
        if (!text) return;

        var btn = $j('#inbox-add-note-btn');
        btn.prop('disabled', true).html('<span class="glyphicon glyphicon-refresh inbox-spinner"></span> Adding...');

        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/note/',
            { note_text: text },
            function() {
                location.reload();
            },
            function(msg) {
                btn.prop('disabled', false).text('Add Note');
                alert('Failed to add note: ' + msg);
            }
        );
    }

    function deleteNote(noteId) {
        if (!confirm('Delete this note?')) return;

        ajaxPost(
            '/manage/inbox/note/' + noteId + '/delete/',
            {},
            function() { $j('#inbox-note-' + noteId).fadeOut(300, function() { $j(this).remove(); }); },
            function(msg) { alert('Failed to delete note: ' + msg); }
        );
    }

    // ── Labels ──
    function addLabel(threadId, labelId) {
        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/labels/',
            { action: 'add', label_id: labelId },
            function() { location.reload(); },
            function(msg) { alert('Failed to add label: ' + msg); }
        );
    }

    function removeLabel(threadId, labelId) {
        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/labels/',
            { action: 'remove', label_id: labelId },
            function() { location.reload(); },
            function(msg) { alert('Failed to remove label: ' + msg); }
        );
    }

    function toggleLabelDropdown() {
        $j('#inbox-label-dropdown').toggleClass('open');
    }

    // ── Canned Responses ──
    function loadCannedResponse(selectEl) {
        var val = $j(selectEl).val();
        if (!val) return;
        // canned_responses_data is set in the template
        if (typeof window.inboxCannedResponses !== 'undefined') {
            for (var i = 0; i < window.inboxCannedResponses.length; i++) {
                if (String(window.inboxCannedResponses[i].id) === String(val)) {
                    var textarea = $j('#id_body');
                    var existing = textarea.val().trim();
                    if (existing && !confirm('Replace your current draft with this template?')) {
                        $j(selectEl).val('');  // Reset dropdown
                        return;
                    }
                    textarea.val(window.inboxCannedResponses[i].body);
                    break;
                }
            }
        }
    }

    // ── Bulk Actions ──
    var selectedThreads = {};

    function toggleBulkCheckbox(checkbox) {
        var tid = $j(checkbox).val();
        if (checkbox.checked) {
            selectedThreads[tid] = true;
        } else {
            delete selectedThreads[tid];
        }
        updateBulkBar();
    }

    function toggleSelectAll(checkbox) {
        $j('.inbox-row-checkbox').prop('checked', checkbox.checked);
        selectedThreads = {};
        if (checkbox.checked) {
            $j('.inbox-row-checkbox').each(function() {
                selectedThreads[$j(this).val()] = true;
            });
        }
        updateBulkBar();
    }

    function updateBulkBar() {
        var count = Object.keys(selectedThreads).length;
        var bar = $j('#inbox-bulk-bar');
        if (count > 0) {
            bar.addClass('active');
            $j('#inbox-bulk-count').text(count + ' selected (this page)');
        } else {
            bar.removeClass('active');
        }
    }

    function bulkAction(action) {
        var ids = Object.keys(selectedThreads);
        if (ids.length === 0) return;
        if (!confirm('Apply "' + action + '" to ' + ids.length + ' thread(s)?')) return;

        ajaxPost(
            '/manage/inbox/bulk/',
            { action: action, 'thread_ids[]': ids },
            function() { location.reload(); },
            function(msg) { alert('Bulk action failed: ' + msg); }
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

    // ── Forward Thread ──
    function openForwardModal() {
        $j('#inbox-forward-modal').addClass('open');
        $j('#inbox-forward-email').focus();
    }

    function closeForwardModal() {
        $j('#inbox-forward-modal').removeClass('open');
    }

    function forwardThread(threadId) {
        var emailTo = $j('#inbox-forward-email').val().trim();
        if (!emailTo) { alert('Please enter an email address'); return; }

        var btn = $j('#inbox-forward-btn');
        btn.prop('disabled', true).html('<span class="glyphicon glyphicon-refresh inbox-spinner"></span> Sending...');

        ajaxPost(
            '/manage/inbox/thread/' + threadId + '/forward/',
            { email: emailTo },
            function(resp) {
                closeForwardModal();
                btn.prop('disabled', false).text('Send');
                showFeedback('#thread-update-feedback', 'Forwarded!', false);
            },
            function(msg) {
                btn.prop('disabled', false).text('Send');
                alert('Forward failed: ' + msg);
            }
        );
    }

    // ── Label Color Contrast ──
    function getLabelTextColor(bgColor) {
        if (!bgColor || bgColor[0] !== '#') return '#fff';
        var hex = bgColor.replace('#', '');
        if (hex.length === 3) hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
        var r = parseInt(hex.substr(0, 2), 16);
        var g = parseInt(hex.substr(2, 2), 16);
        var b = parseInt(hex.substr(4, 2), 16);
        // W3C relative luminance
        var luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
        return luminance > 0.6 ? '#1a1a1a' : '#fff';
    }

    function applyLabelContrast() {
        $j('.inbox-label-pill').each(function() {
            var el = $j(this);
            var bg = el.css('background-color');
            // Convert rgb(r,g,b) to hex
            if (bg && bg.indexOf('rgb') === 0) {
                var parts = bg.match(/\d+/g);
                if (parts && parts.length >= 3) {
                    var hex = '#' +
                        ('0' + parseInt(parts[0]).toString(16)).slice(-2) +
                        ('0' + parseInt(parts[1]).toString(16)).slice(-2) +
                        ('0' + parseInt(parts[2]).toString(16)).slice(-2);
                    el.css('color', getLabelTextColor(hex));
                }
            } else if (bg && bg[0] === '#') {
                el.css('color', getLabelTextColor(bg));
            }
        });
    }

    // ── Initialization ──
    $j(function() {
        renderAvatars();
        renderRelativeDates();
        applyLabelContrast();

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

        // Close label dropdown on outside click
        $j(document).on('click', function(e) {
            if (!$j(e.target).closest('.inbox-label-dropdown, .inbox-add-label-btn').length) {
                $j('#inbox-label-dropdown').removeClass('open');
            }
        });

        // Close forward modal on overlay click
        $j('#inbox-forward-modal').on('click', function(e) {
            if ($j(e.target).is('#inbox-forward-modal')) closeForwardModal();
        });
    });

    function getThreadId() {
        var match = window.location.pathname.match(/\/manage\/inbox\/thread\/(\d+)/);
        return match ? match[1] : null;
    }

    return {
        markRead: markRead,
        updateThread: updateThread,
        addNote: addNote,
        deleteNote: deleteNote,
        addLabel: addLabel,
        removeLabel: removeLabel,
        toggleLabelDropdown: toggleLabelDropdown,
        loadCannedResponse: loadCannedResponse,
        toggleBulkCheckbox: toggleBulkCheckbox,
        toggleSelectAll: toggleSelectAll,
        bulkAction: bulkAction,
        quickAssignMe: quickAssignMe,
        quickClose: quickClose,
        openForwardModal: openForwardModal,
        closeForwardModal: closeForwardModal,
        forwardThread: forwardThread,
        renderAvatars: renderAvatars,
        renderRelativeDates: renderRelativeDates,
        getAvatarColor: getAvatarColor,
        getInitials: getInitials,
        getLabelTextColor: getLabelTextColor
    };
})();
