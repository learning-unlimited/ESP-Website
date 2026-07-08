/*
 * module_timeline.js
 * Script for interactive module management page.
 */

var $j = jQuery.noConflict();

$j(document).ready(function() {
    var programUrlBase = JSON.parse(document.getElementById('program-url-base').textContent);
    var csrfToken = JSON.parse(document.getElementById('csrf-token-data').textContent);
    var constraints = JSON.parse(document.getElementById('module-constraints-data').textContent);

    var currentView = 'student'; // 'student', 'teacher', 'split'
    var allModules = { learn: [], teach: [] };
    var activeModule = null;    // currently editing
    var activeModuleType = null; // 'student' or 'teacher'

    var timelineStart = null;
    var timelineEnd = null;
    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    var nowInterval = null;

    // Elements
    var $studentTab  = $j('#btnStudentTab');
    var $teacherTab  = $j('#btnTeacherTab');
    var $splitTab    = $j('#btnSplitTab');
    var $studentContent = $j('#studentContent');
    var $teacherContent = $j('#teacherContent');

    var $editOverlay = $j('#editOverlay');
    var $editPanel   = $j('#editPanel');
    var $addOverlay  = $j('#addOverlay');
    var $addDrawer   = $j('#addDrawer');

    // ──────────────────────────────────────────────────────────────
    // Toast Notifications (replaces alert())
    // ──────────────────────────────────────────────────────────────
    function showToast(msg, type) {
        // type = 'success' | 'error'
        var $toast = $j('<div>').addClass('tl-toast tl-toast-' + (type || 'success')).text(msg);
        $j('body').append($toast);
        setTimeout(function() { $toast.addClass('tl-toast-visible'); }, 10);
        setTimeout(function() {
            $toast.removeClass('tl-toast-visible');
            setTimeout(function() { $toast.remove(); }, 300);
        }, 3000);
    }

    // ──────────────────────────────────────────────────────────────
    // API: Load modules
    // ──────────────────────────────────────────────────────────────
    function loadModules() {
        $j.ajax({
            url: '/manage/' + programUrlBase + '/module_schedule',
            method: 'GET',
            success: function(response) {
                if (response.modules) {
                    allModules.learn = response.modules.learn || [];
                    allModules.teach = response.modules.teach || [];
                    computeTimelineDates();
                    renderGridHeaders();
                    renderTimeline('student');
                    renderTimeline('teacher');
                    updateTabCounts();
                } else {
                    showToast('Failed to load modules.', 'error');
                }
            },
            error: function() {
                showToast('Network error while loading modules.', 'error');
            }
        });
    }

    function updateTabCounts() {
        $j('#studentCount').text(allModules.learn.length);
        $j('#teacherCount').text(allModules.teach.length);
    }

    function computeTimelineDates() {
        var minDate = null;
        var maxDate = null;
        
        var all = allModules.learn.concat(allModules.teach);
        
        $j.each(all, function(i, mod) {
            if (mod.start_date) {
                var d = new Date(mod.start_date);
                if (!minDate || d < minDate) minDate = new Date(d);
            }
            if (mod.end_date) {
                var d = new Date(mod.end_date);
                if (!maxDate || d > maxDate) maxDate = new Date(d);
            }
        });
        
        if (!minDate) minDate = new Date();
        if (!maxDate) {
            maxDate = new Date(minDate);
            maxDate.setMonth(maxDate.getMonth() + 3);
        }
        
        var now = new Date();
        if (now < minDate) minDate = new Date(now);
        if (now > maxDate) maxDate = new Date(now);
        
        // Add padding (35 days before so the red line doesn't overlap labels, and 14 days after)
        minDate.setDate(minDate.getDate() - 35);
        maxDate.setDate(maxDate.getDate() + 14);
        
        timelineStart = minDate;
        
        var totalMs = maxDate - minDate;
        var stepMs = 15 * 24 * 60 * 60 * 1000; // strictly 15 days
        window.timelineNumLabels = Math.ceil(totalMs / stepMs);
        if (window.timelineNumLabels < 7) {
            window.timelineNumLabels = 7;
        }
        
        timelineEnd = new Date(timelineStart.getTime() + (window.timelineNumLabels * stepMs));
    }

    function updateNowLine() {
        if (!timelineStart || !timelineEnd) return;
        var now = new Date();
        var totalMs = timelineEnd - timelineStart;
        var nowPct = ((now - timelineStart) / totalMs) * 100;
        if (nowPct < 0) nowPct = 0;
        if (nowPct > 100) nowPct = 100;
        
        $j('.tl-now-line, .tl-now-badge').css('left', nowPct + '%');
    }

    function renderGridHeaders() {
        var $headers = $j('.tl-grid-labels');
        $headers.empty();
        
        var numLabels = window.timelineNumLabels || 7;
        var totalMs = timelineEnd - timelineStart;
        var pctPerLabel = 100 / numLabels;
        
        // Dynamically size the grid to ensure min-width makes sense
        // 900px was for 7 columns. If more, stretch proportionately.
        var minScrollWidth = numLabels * (900 / 7);
        $j('.tl-header-scroll-content, .tl-grid-scroll-content, .tl-blocks, .tl-now-wrapper').css('min-width', minScrollWidth + 'px');
        
        $j('.timeline-grid').css('background-size', pctPerLabel + '% 100%');
        
        for (var i = 0; i < numLabels; i++) {
            var stepMs = totalMs / numLabels;
            var d = new Date(timelineStart.getTime() + (i * stepMs));
            var labelText = months[d.getMonth()] + ' ' + d.getDate();
            
            var $labelBox = $j('<div>').addClass('tl-grid-label').css({
                width: pctPerLabel + '%',
                position: 'relative',
                borderLeft: 'none'
            });
            
            var $span = $j('<span>').css({
                position: 'absolute',
                left: i === 0 ? '8px' : '0',
                transform: i === 0 ? 'none' : 'translateX(-50%)',
                bottom: '4px'
            }).text(labelText);
            
            $labelBox.append($span);
            $headers.append($labelBox);
        }
        
        $j('.tl-now-badge').remove();
        var $nowBadge = $j('<div>').addClass('tl-now-badge')
            .css({
                position: 'absolute',
                bottom: '4px',
                transform: 'translateX(-50%)',
                whiteSpace: 'nowrap',
                zIndex: 30
            })
            .text('NOW');
            
        $headers.append($nowBadge);
        
        updateNowLine();
        if (!nowInterval) {
            nowInterval = setInterval(updateNowLine, 60000);
        }
    }

    // ──────────────────────────────────────────────────────────────
    // Timeline block positioning
    // ──────────────────────────────────────────────────────────────
    function calculatePosition(mod) {
        var isAlwaysOn = !mod.start_date && !mod.end_date;
        var now = new Date();
        
        if (isAlwaysOn) {
            return {
                left: '0%',
                width: '100%',
                isActive: true,
                isAlwaysOn: true
            };
        }

        var sDate = mod.start_date ? new Date(mod.start_date) : timelineStart;
        var eDate = mod.end_date ? new Date(mod.end_date) : timelineEnd;
        
        var isActive = (now >= sDate && now <= eDate);
        
        var totalMs = timelineEnd - timelineStart;
        var leftMs = sDate - timelineStart;
        var widthMs = eDate - sDate;
        
        var leftPct = Math.max(0, (leftMs / totalMs) * 100);
        var widthPct = (widthMs / totalMs) * 100;
        
        if (leftPct + widthPct > 100) {
            widthPct = 100 - leftPct;
        }
        if (widthPct < 0) widthPct = 0;

        return {
            left: leftPct + '%',
            width: Math.max(0.5, widthPct) + '%',
            isActive: isActive,
            isAlwaysOn: false
        };
    }

    // ──────────────────────────────────────────────────────────────
    // Render one timeline panel (student or teacher)
    // ──────────────────────────────────────────────────────────────
    function renderTimeline(type) {
        var modules  = type === 'student' ? allModules.learn : allModules.teach;
        var $sidebar = $j('#' + type + 'Sidebar');
        var $grid    = $j('#' + type + 'Grid');

        $sidebar.empty();
        $grid.empty();

        $j.each(modules, function(index, mod) {
            var c       = constraints[String(mod.id)] || {};
            var isLocked = c.position_locked;
            var pos     = calculatePosition(mod);

            // ── Sidebar row ──────────────────────────────────────
            var $row = $j('<div>').addClass('tl-row-label').on('click', function() {
                openEditPanel(mod, type);
            });
            if (isLocked) { $row.addClass('tl-row-locked'); }

            // Add status classes based on timeline position
            if (pos.isAlwaysOn) {
                $row.addClass('status-always-on');
            } else if (pos.isActive) {
                $row.addClass('status-active');
            } else {
                $row.addClass('status-inactive');
            }

            var $idx = $j('<div>').addClass('tl-row-index').text(index + 1);
            var $text = $j('<div>').addClass('tl-row-text');
            
            // Title + Badge wrapper (keeps badges inline next to title text)
            var $titleWrapper = $j('<div>').css({
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                minWidth: 0,
                width: '100%'
            });
            
            var $title = $j('<span>').addClass('tl-row-title').text(
                mod.link_title || mod.admin_title || ('Module ' + mod.id)
            );
            $titleWrapper.append($title);

            // Lock + Req badges
            var $badges = $j('<div>').addClass('tl-row-badges');
            if (isLocked && !c.required_locked && !c.not_required_locked) {
                $badges.append($j('<span>').addClass('tl-badge tl-badge-lock').attr('title', 'Position locked').text('🔒'));
            }
            if (c.required_locked) {
                $badges.append($j('<span>').addClass('tl-badge tl-badge-req-locked').attr('title', 'Must be required').text('🔒 REQ'));
            } else if (mod.required) {
                $badges.append($j('<span>').addClass('tl-badge tl-badge-req-locked').text('REQ'));
            }
            
            if (c.not_required_locked) {
                $badges.append($j('<span>').addClass('tl-badge tl-badge-not-req').attr('title', 'Cannot be required').text('🔒 OPT'));
            } else if (!mod.required && !c.required_locked) {
                $badges.append($j('<span>').addClass('tl-badge tl-badge-not-req').text('OPT'));
            }
            $titleWrapper.append($badges);
            $text.append($titleWrapper);

            // Active now label
            if (pos.isActive && !pos.isAlwaysOn) {
                var $statusText = $j('<div>').addClass('tl-active-now-text');
                $statusText.append($j('<span>').addClass('tl-active-now-dot').text('●'));
                $statusText.append($j('<span>').text('Active now'));
                $titleWrapper.append($statusText);
            }

            $row.append($idx).append($text);
            $sidebar.append($row);

            // ── Grid block ───────────────────────────────────────
            var $blockRow = $j('<div>').addClass('tl-block-row');
            var $block    = $j('<div>').addClass('tl-block')
                .css({ left: pos.left, width: pos.width })
                .on('click', function() { openEditPanel(mod, type); });

            var $leftSticky = $j('<span>').addClass('tl-block-label').text(mod.link_title || mod.admin_title).css({
                position: 'sticky',
                left: '12px'
            });

            var $rightSticky = $j('<div>').css({
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                position: 'sticky',
                right: '12px'
            });

            if (pos.isAlwaysOn) {
                $block.addClass('block-always-on');
                $rightSticky.append($j('<span>').addClass('tl-block-sub').text('Always On'));
                if (mod.required) {
                    $rightSticky.append($j('<span>').addClass('badge-req').text('REQ'));
                }
            } else {
                var isSolid = type === 'student' ? 'block-solid-student' : 'block-solid-teacher';
                var isFaded = type === 'student' ? 'block-faded-student' : 'block-faded-teacher';
                $block.addClass(pos.isActive ? isSolid : isFaded);
                if (mod.required) {
                    $rightSticky.append($j('<span>').addClass('badge-req').text('REQ'));
                }
            }
            
            $block.append($leftSticky);
            if ($rightSticky.children().length > 0) {
                $block.append($rightSticky);
            }
            $blockRow.append($block);
            $grid.append($blockRow);
        });
    }

    // ──────────────────────────────────────────────────────────────
    // Legend bar – updates dynamically when switching tabs
    // ──────────────────────────────────────────────────────────────
    function updateLegend(view) {
        var isTeacher = (view === 'teacher');
        var activeColor   = isTeacher ? 'var(--brand-teacher)' : 'var(--brand-student)';
        var scheduledBg   = isTeacher ? '#f5f3ff' : '#eff6ff';
        var scheduledBorder = isTeacher ? '#e9d5ff' : '#bfdbfe';
        var activeLabel   = isTeacher ? 'Teacher Active' : 'Student Active';
        var scheduledLabel = isTeacher ? 'Teacher Scheduled' : 'Student Scheduled';

        // For split view show both
        if (view === 'split') {
            $j('#legendActive').css('background-color', '#3b82f6').next('span').text('Student Active');
            $j('#legendScheduled').css({ 'background-color': '#eff6ff', 'border': '1px solid #bfdbfe' }).next('span').text('Student Scheduled');
            $j('#legendTeacherActive').show();
            $j('#legendTeacherScheduled').show();
            return;
        }

        $j('#legendActive').css('background-color', activeColor);
        $j('#legendActiveLabel').text(activeLabel);
        $j('#legendScheduled').css({ 'background-color': scheduledBg, 'border': '1px solid ' + scheduledBorder });
        $j('#legendScheduledLabel').text(scheduledLabel);
        $j('#legendTeacherActive').hide();
        $j('#legendTeacherScheduled').hide();
    }

    // ──────────────────────────────────────────────────────────────
    // View Switching
    // ──────────────────────────────────────────────────────────────
    window.switchView = function(view) {
        currentView = view;

        // Reset all tabs
        $studentTab.removeClass('active-student');
        $teacherTab.removeClass('active-teacher');
        $splitTab.removeClass('active-split');

        var $workspace = $j('.tl-workspace');
        $workspace.removeClass('split-view');

        if (view === 'student') {
            $studentTab.addClass('active-student');
            $studentContent.removeClass('hidden');
            $teacherContent.addClass('hidden');
        } else if (view === 'teacher') {
            $teacherTab.addClass('active-teacher');
            $teacherContent.removeClass('hidden');
            $studentContent.addClass('hidden');
        } else { // split
            $splitTab.addClass('active-split');
            $workspace.addClass('split-view');
            $studentContent.removeClass('hidden');
            $teacherContent.removeClass('hidden');
        }

        updateLegend(view);
    };

    // ──────────────────────────────────────────────────────────────
    // Edit Panel
    // ──────────────────────────────────────────────────────────────
    function openEditPanel(mod, type) {
        activeModule     = mod;
        activeModuleType = type;
        var c = constraints[String(mod.id)] || {};

        $j('#editPanel').removeClass('theme-student theme-teacher').addClass('theme-' + type);
        $j('#editSubtitle').text('Editing: ' + (mod.link_title || mod.admin_title || ('Module ' + mod.id)));
        $j('#editLabel').val(mod.link_title || '');
        $j('#editReqLabel').val(mod.required_label || '');

        // Dates
        $j('#editStart').val(mod.start_date ? mod.start_date.substring(0, 16) : '');
        $j('#editEnd').val(mod.end_date   ? mod.end_date.substring(0, 16)   : '');

        // Required toggle
        if (mod.required) {
            $j('#reqToggle').addClass('on');
            $j('#reqLabel').text('Required');
        } else {
            $j('#reqToggle').removeClass('on');
            $j('#reqLabel').text('Optional');
        }

        // Constraint locks
        if (c.required_locked || c.not_required_locked) {
            $j('#reqToggle').prop('disabled', true).css('opacity', '0.5');
            $j('#reqLockMsg').text('Required status is fixed for this module.').show();
        } else {
            $j('#reqToggle').prop('disabled', false).css('opacity', '1');
            $j('#reqLockMsg').hide();
        }

        $editOverlay.addClass('active');
        $editPanel.addClass('active');
    }

    window.closeEditPanel = function() {
        $editPanel.removeClass('active');
        $editOverlay.removeClass('active');
        activeModule     = null;
        activeModuleType = null;
    };

    window.toggleReq = function() {
        if ($j('#reqToggle').prop('disabled')) return;
        var isOn = $j('#reqToggle').hasClass('on');
        $j('#reqToggle').toggleClass('on', !isOn);
        $j('#reqLabel').text(isOn ? 'Optional' : 'Required');
    };

    $j('#editSaveBtn').on('click', function() {
        if (!activeModule) return;

        var payload = {
            module_id:      activeModule.id,
            link_title:     $j('#editLabel').val(),
            required_label: $j('#editReqLabel').val(),
            start_date:     $j('#editStart').val() || null,
            end_date:       $j('#editEnd').val()   || null,
            required:       $j('#reqToggle').hasClass('on'),
            seq:            activeModule.seq
        };

        $j('#editSaveBtn').prop('disabled', true).text('Saving…');

        $j.ajax({
            url: '/manage/' + programUrlBase + '/module_schedule/update',
            method: 'POST',
            data: JSON.stringify(payload),
            contentType: 'application/json',
            headers: { 'X-CSRFToken': csrfToken },
            success: function(res) {
                $j('#editSaveBtn').prop('disabled', false).text('Save Changes');
                if (res.success) {
                    showToast('Module saved successfully.', 'success');
                    closeEditPanel();
                    loadModules();
                } else {
                    showToast('Error: ' + (res.error || 'Unknown error'), 'error');
                }
            },
            error: function(xhr) {
                $j('#editSaveBtn').prop('disabled', false).text('Save Changes');
                var msg = 'An error occurred while saving.';
                try { msg = JSON.parse(xhr.responseText).error || msg; } catch(e) {}
                showToast(msg, 'error');
            }
        });
    });

    // ──────────────────────────────────────────────────────────────
    // Add Drawer & Save Modules
    // ──────────────────────────────────────────────────────────────
    window.openAddDrawer = function() {
        $addOverlay.addClass('active');
        $addDrawer.addClass('active');
    };
    window.closeAddDrawer = function() {
        $addDrawer.removeClass('active');
        $addOverlay.removeClass('active');
    };

    window.saveModules = function() {
        var addIds = [];
        var removeIds = [];
        
        $j('.tl-add-checkbox').each(function() {
            var isChecked = $j(this).prop('checked');
            var val = $j(this).val();
            // Since initial state checked attribute is set by django,
            // we can check if it changed by comparing to the defaultChecked property.
            if (isChecked && !this.defaultChecked) {
                addIds.push(val);
            } else if (!isChecked && this.defaultChecked) {
                removeIds.push(val);
            }
        });

        if (addIds.length === 0 && removeIds.length === 0) {
            closeAddDrawer();
            return;
        }

        var payload = new URLSearchParams();
        addIds.forEach(function(id) { payload.append('add_modules[]', id); });
        removeIds.forEach(function(id) { payload.append('remove_modules[]', id); });
        // Include CSRF token in payload if using standard form POST, but we use headers.
        
        var $btn = $j('#addDrawer .tl-btn-primary');
        var oldText = $btn.text();
        $btn.prop('disabled', true).text('Updating...');

        $j.ajax({
            url: '/manage/' + programUrlBase + '/update_program_modules',
            method: 'POST',
            data: payload.toString(),
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            success: function(res) {
                $btn.prop('disabled', false).text(oldText);
                if (res.status === 'success') {
                    showToast('Modules updated successfully.', 'success');
                    closeAddDrawer();
                    window.location.reload();
                } else {
                    showToast('Error: ' + (res.message || 'Unknown error'), 'error');
                }
            },
            error: function(xhr) {
                $btn.prop('disabled', false).text(oldText);
                showToast('An error occurred while updating modules.', 'error');
            }
        });
    };

    // ──────────────────────────────────────────────────────────────
    // Init
    // ──────────────────────────────────────────────────────────────
    updateLegend('student');
    loadModules();

    // Sync header scroll with grid scroll
    $j('.tl-main-grid').on('scroll', function() {
        var scrollLeft = $j(this).scrollLeft();
        $j(this).closest('.tl-content').find('.tl-header-scroll-content').css('transform', 'translateX(-' + scrollLeft + 'px)');
    });

    // Hover sync to show NOW badge when hovering over NOW line
    $j(document).on('mouseenter', '.tl-now-line', function() {
        $j(this).closest('.tl-content').find('.tl-now-badge').css('opacity', '1');
    }).on('mouseleave', '.tl-now-line', function() {
        $j(this).closest('.tl-content').find('.tl-now-badge').css('opacity', '0');
    });
});
