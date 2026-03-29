/**
 * Onsite Admin Core - Reusable utilities and API client
 * Provides shared functionality for onsite admin modules
 */
var OnsiteAdminCore = (function() {
    "use strict";

    // ========== API Client ==========

    var API = {
        /**
         * Fetch all sections with enrollment/attendance data
         * @param {string} programUrl - Program URL base
         * @param {object} params - Query parameters (e.g., {timeslot: 123})
         * @returns {Promise} Promise resolving to section data
         */
        getSections: function(programUrl, params) {
            return $j.ajax({
                url: '/onsite/' + programUrl + '/onsiteadmin_sections_api',
                data: params || {},
                dataType: 'json'
            });
        },

        /**
         * Toggle registration status for a section
         * @param {string} programUrl - Program URL base
         * @param {number} sectionId - Section ID
         * @param {string} action - 'open' or 'close'
         * @returns {Promise}
         */
        toggleRegistration: function(programUrl, sectionId, action) {
            return $j.ajax({
                url: '/onsite/' + programUrl + '/onsiteadmin_toggle_registration',
                method: 'POST',
                data: {
                    section_id: sectionId,
                    action: action
                },
                dataType: 'json'
            });
        },

        /**
         * Set section capacity
         * @param {string} programUrl - Program URL base
         * @param {number} sectionId - Section ID
         * @param {number} capacity - New capacity value
         * @returns {Promise}
         */
        setCapacity: function(programUrl, sectionId, capacity) {
            return $j.ajax({
                url: '/onsite/' + programUrl + '/onsiteadmin_set_capacity',
                method: 'POST',
                data: {
                    section_id: sectionId,
                    capacity: capacity
                },
                dataType: 'json'
            });
        }
    };

    // ========== UI Utilities ==========

    var UI = {
        /**
         * Render a section status badge
         * @param {object} section - Section data
         * @returns {string} HTML string for status badge
         */
        renderStatusBadge: function(section) {
            var statusClass, statusText;
            if (!section.is_reg_open) {
                statusClass = 'status-closed';
                statusText = 'Closed';
            } else if (section.is_full) {
                statusClass = 'status-full';
                statusText = 'Full';
            } else {
                statusClass = 'status-open';
                statusText = 'Open';
            }
            return '<span class="class-status ' + statusClass + '">' + statusText + '</span>';
        },

        /**
         * Render enrollment progress bars
         * @param {number} enrolled - Enrolled count
         * @param {number} attending - Attending count
         * @param {number} capacity - Section capacity
         * @returns {string} HTML string for progress bars
         */
        renderProgressBar: function(enrolled, attending, capacity) {
            var enrolledPct = capacity > 0 ? Math.min(Math.round((enrolled / capacity) * 100), 100) : 0;
            var attendingPct = capacity > 0 ? Math.min(Math.round((attending / capacity) * 100), 100) : 0;

            var progressClass = '';
            if (enrolledPct >= 100) progressClass = 'progress-danger';
            else if (enrolledPct >= 75) progressClass = 'progress-warning';

            return '<div class="enrollment-numbers">' +
                '<span>Enrolled: <strong>' + enrolled + '</strong> / ' + capacity + '</span>' +
                '<span>Attending: <strong>' + attending + '</strong></span>' +
                '</div>' +
                '<div class="progress-bar-container">' +
                '<div class="progress-bar progress-enrolled ' + progressClass + '" style="width:' + enrolledPct + '%"></div>' +
                '<div class="progress-bar progress-attending" style="width:' + attendingPct + '%"></div>' +
                '</div>' +
                '<div class="progress-legend">' +
                '<span class="legend-item"><span class="legend-color legend-enrolled"></span> Enrolled</span>' +
                '<span class="legend-item"><span class="legend-color legend-attending"></span> Attending</span>' +
                '</div>';
        },

        /**
         * Update timestamp display
         * @param {string} timestamp - ISO timestamp or Date object
         */
        updateTimestamp: function(timestamp, elementId) {
            var d = timestamp instanceof Date ? timestamp : new Date(timestamp);
            var timeStr = d.toLocaleTimeString();
            $j('#' + (elementId || 'last-updated')).text('Updated: ' + timeStr);
        },

        /**
         * Show a notification message
         * @param {string} message - Message text
         * @param {string} type - 'success', 'error', 'warning'
         */
        notify: function(message, type) {
            // Simple alert for now - can be enhanced with toast notifications
            if (type === 'error') {
                alert('Error: ' + message);
            } else if (type === 'success') {
                console.log('Success: ' + message);
            }
        }
    };

    // ========== Utility Functions ==========

    var Utils = {
        /**
         * Escape HTML to prevent XSS
         */
        escapeHtml: function(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
        },

        /**
         * Escape attribute values
         */
        escapeAttr: function(str) {
            if (!str) return '';
            return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
        },

        /**
         * Debounce function calls
         */
        debounce: function(func, wait) {
            var timeout;
            return function() {
                var context = this, args = arguments;
                clearTimeout(timeout);
                timeout = setTimeout(function() {
                    func.apply(context, args);
                }, wait);
            };
        }
    };

    // Public API
    return {
        API: API,
        UI: UI,
        Utils: Utils
    };

})();
