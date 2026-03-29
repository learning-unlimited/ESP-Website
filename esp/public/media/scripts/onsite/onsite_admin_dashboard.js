/**
 * Onsite Admin Dashboard - Dashboard-specific logic
 * Depends on: onsite_admin_core.js
 */
(function() {
    "use strict";

    var Core = window.OnsiteAdminCore;
    var refreshInterval = 30; // seconds
    var refreshTimer = null;
    var currentFilters = {
        timeslot: '',
        search: '',
        status: ''
    };

    // ========== Initialization ==========

    $j(document).ready(function() {
        initTabs();
        initFilters();
        initActions();
        loadSections();
        startAutoRefresh();
    });

    // ========== Tab Navigation ==========

    function initTabs() {
        $j('.tab-btn').on('click', function() {
            var tab = $j(this).data('tab');
            $j('.tab-btn').removeClass('active');
            $j(this).addClass('active');
            $j('.tab-content').removeClass('active');
            $j('#tab-' + tab).addClass('active');
        });
    }

    // ========== Filters ==========

    function initFilters() {
        $j('#filter-timeslot').on('change', function() {
            currentFilters.timeslot = $j(this).val();
            loadSections();
        });

        $j('#filter-search').on('input', Core.Utils.debounce(function() {
            currentFilters.search = $j(this).val().toLowerCase();
            filterDisplayedSections();
        }, 300));

        $j('#filter-status').on('change', function() {
            currentFilters.status = $j(this).val();
            filterDisplayedSections();
        });

        // Settings: refresh interval
        $j('#setting-refresh-interval').on('change', function() {
            refreshInterval = parseInt($j(this).val()) || 30;
            startAutoRefresh();
        });
    }

    // ========== Actions ==========

    function initActions() {
        // Manual refresh
        $j('#btn-refresh').on('click', function() {
            loadSections();
        });

        // Bulk close all registration
        $j('#btn-close-all-reg').on('click', function() {
            if (confirm('Close registration for ALL visible sections?')) {
                bulkToggleRegistration('close');
            }
        });

        // Bulk open all registration
        $j('#btn-open-all-reg').on('click', function() {
            if (confirm('Open registration for ALL visible sections?')) {
                bulkToggleRegistration('open');
            }
        });

        // Delegated events for dynamically-created elements
        $j(document).on('click', '.btn-toggle-reg', function() {
            var sectionId = $j(this).data('section-id');
            var action = $j(this).data('action');
            toggleRegistration(sectionId, action);
        });

        $j(document).on('click', '#btn-set-capacity', function() {
            var sectionId = $j(this).data('section-id');
            var capacity = $j('#input-capacity').val();
            setCapacity(sectionId, capacity);
        });
    }

    // ========== Data Loading ==========

    function loadSections() {
        var params = {};
        if (currentFilters.timeslot) {
            params.timeslot = currentFilters.timeslot;
        }

        $j('#loading-indicator').show();

        Core.API.getSections(PROGRAM_URL, params)
            .done(function(data) {
                renderStats(data.stats);
                renderSections(data.sections);
                Core.UI.updateTimestamp(data.timestamp);
                $j('#loading-indicator').hide();
            })
            .fail(function() {
                $j('#loading-indicator').text('Error loading data. Will retry...');
            });
    }

    // ========== Rendering ==========

    function renderStats(stats) {
        $j('#stat-checked-in').text(stats.checked_in_students);
        $j('#stat-total-enrolled').text(stats.total_enrolled);
        $j('#stat-total-attending').text(stats.total_attending);
        $j('#stat-num-sections').text(stats.num_sections);
    }

    function renderSections(sections) {
        var container = $j('#class-list');
        container.find('.class-card').remove();

        sections.sort(function(a, b) {
            if (a.times < b.times) return -1;
            if (a.times > b.times) return 1;
            return a.emailcode.localeCompare(b.emailcode);
        });

        for (var i = 0; i < sections.length; i++) {
            var card = buildSectionCard(sections[i]);
            container.append(card);
        }

        filterDisplayedSections();
    }

    function buildSectionCard(sec) {
        var html = '<div class="class-card" ' +
            'data-section-id="' + sec.id + '" ' +
            'data-title="' + Core.Utils.escapeAttr(sec.title.toLowerCase()) + '" ' +
            'data-emailcode="' + Core.Utils.escapeAttr(sec.emailcode.toLowerCase()) + '" ' +
            'data-status="' + (sec.is_full ? 'full' : (sec.is_reg_open ? 'open' : 'closed')) + '">' +
            '<div class="class-card-header">' +
                '<div class="class-card-title">' +
                    '<a href="/onsite/' + PROGRAM_URL + '/onsiteadmin_section_detail/' + sec.id + '">' +
                        '<span class="class-code">' + Core.Utils.escapeHtml(sec.emailcode) + '</span> ' +
                        Core.Utils.escapeHtml(sec.title) +
                    '</a>' +
                '</div>' +
                Core.UI.renderStatusBadge(sec) +
            '</div>' +
            '<div class="class-card-meta">' +
                '<span>' + Core.Utils.escapeHtml(sec.teachers) + '</span>' +
                '<span>' + Core.Utils.escapeHtml(sec.rooms) + '</span>' +
                '<span>' + Core.Utils.escapeHtml(sec.times) + '</span>' +
            '</div>' +
            '<div class="class-card-enrollment">' +
                Core.UI.renderProgressBar(sec.enrolled, sec.attending, sec.capacity) +
            '</div>' +
            '<div class="class-card-actions">' +
                '<button class="btn btn-sm btn-toggle-reg ' + (sec.is_reg_open ? 'btn-warning' : 'btn-success') + '" ' +
                    'data-section-id="' + sec.id + '" ' +
                    'data-action="' + (sec.is_reg_open ? 'close' : 'open') + '">' +
                    (sec.is_reg_open ? 'Close Reg' : 'Open Reg') +
                '</button>' +
            '</div>' +
        '</div>';

        return html;
    }

    // ========== Client-side Filtering ==========

    function filterDisplayedSections() {
        $j('.class-card').each(function() {
            var card = $j(this);
            var show = true;

            // Search filter
            if (currentFilters.search) {
                var title = card.data('title') || '';
                var code = card.data('emailcode') || '';
                if (title.indexOf(currentFilters.search) === -1 &&
                    code.indexOf(currentFilters.search) === -1) {
                    show = false;
                }
            }

            // Status filter
            if (currentFilters.status) {
                var status = card.data('status');
                if (status !== currentFilters.status) {
                    show = false;
                }
            }

            card.toggle(show);
        });
    }

    // ========== AJAX Actions ==========

    function toggleRegistration(sectionId, action) {
        Core.API.toggleRegistration(PROGRAM_URL, sectionId, action)
            .done(function(data) {
                if (data.success) {
                    loadSections();
                    // Update button on section detail page if present
                    updateDetailPageButton(action);
                } else {
                    Core.UI.notify(data.message, 'error');
                }
            })
            .fail(function() {
                Core.UI.notify('Failed to update registration status.', 'error');
            });
    }

    function setCapacity(sectionId, capacity) {
        Core.API.setCapacity(PROGRAM_URL, sectionId, capacity)
            .done(function(data) {
                if (data.success) {
                    Core.UI.notify(data.message, 'success');
                    loadSections();
                } else {
                    Core.UI.notify(data.message, 'error');
                }
            })
            .fail(function() {
                Core.UI.notify('Failed to update capacity.', 'error');
            });
    }

    function bulkToggleRegistration(action) {
        var visibleCards = $j('.class-card:visible');
        var promises = [];

        visibleCards.each(function() {
            var card = $j(this);
            var currentStatus = card.data('status');
            // Only toggle if not already in desired state
            if ((action === 'close' && currentStatus === 'open') ||
                (action === 'open' && currentStatus === 'closed')) {
                var sectionId = card.data('section-id');
                promises.push(Core.API.toggleRegistration(PROGRAM_URL, sectionId, action));
            }
        });

        $j.when.apply($j, promises).then(function() {
            loadSections();
            Core.UI.notify('Bulk operation completed.', 'success');
        });
    }

    function updateDetailPageButton(action) {
        var btn = $j('#btn-toggle-reg');
        if (btn.length) {
            var newAction = action === 'open' ? 'close' : 'open';
            btn.data('action', newAction);
            btn.text(newAction === 'close' ? 'Close Registration' : 'Open Registration');
            btn.toggleClass('btn-warning btn-success');
        }
    }

    // ========== Auto-refresh ==========

    function startAutoRefresh() {
        if (refreshTimer) {
            clearInterval(refreshTimer);
        }
        refreshTimer = setInterval(function() {
            loadSections();
        }, refreshInterval * 1000);
    }

})();
