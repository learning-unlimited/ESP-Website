$j(document).ready(function() {
    // Constraint metadata injected by the server (see admincore.py modules() view).
    // Keys are ProgramModuleObj IDs (as strings).
    // Values: {required_locked, not_required_locked, position_locked} — all booleans.
    // Mirrors the hard-override block that runs on every POST; the UI uses this
    // data to prevent illegal drags rather than silently undoing them on save.
    // Issue #3656.
    var constraints = JSON.parse(document.getElementById('module-constraints-data').textContent);

    // Show a brief dismissible notice when a cross-list drop is rejected.
    // Positioned near the mouse cursor so the user sees it immediately.
    function showConstraintMessage(msg, event) {
        var $msg = $j('#module-constraint-msg');
        $msg.css({ top: event.pageY + 12, left: event.pageX + 12 });
        $msg.text(msg).stop(true, true).fadeIn(150).delay(3000).fadeOut(400);
    }

    // Only position-locked modules are excluded from drag initiation entirely.
    // Modules that are only required_locked or not_required_locked can still be
    // reordered within their own list; they are blocked from crossing lists in
    // makeReceiveHandler below.  The module-locked CSS class (greyed-out, lock
    // icon) is applied server-side only to position_locked modules.
    var lockedSelectors = [];
    $j('.connectedSortable li').each(function() {
        var id = $j(this).attr('id');
        var c = constraints[id];
        if (c && c.position_locked) {
            lockedSelectors.push('#' + id);
        }
    });

    // Extend jQuery UI's default cancel selector so position-locked modules
    // cannot be initiated as drag sources.
    var cancelSelector = 'input,textarea,button,select,option' +
        (lockedSelectors.length ? ',' + lockedSelectors.join(',') : '');

    // Reject cross-list drops for modules whose required status is enforced.
    // Position-locked modules are already non-draggable via cancelSelector, but
    // this guard also covers modules that are only required/not_required locked
    // (e.g. AvailabilityModule) and can be freely reordered within their list.
    function makeReceiveHandler(isRequiredList) {
        return function(event, ui) {
            var id = ui.item.attr('id');
            var c = constraints[id];
            if (!c) { return; }
            if (!isRequiredList && c.required_locked) {
                ui.sender.sortable('cancel');
                showConstraintMessage('This module must always be required and cannot be moved here.', event);
            }
            if (isRequiredList && c.not_required_locked) {
                ui.sender.sortable('cancel');
                showConstraintMessage('This module cannot be required and cannot be moved here.', event);
            }
        };
    }

    $j("#sortable1").sortable({
        containment: "#learn_mods",
        scroll: false,
        connectWith: "#sortable2",
        cancel: cancelSelector,
        receive: makeReceiveHandler(true),
        update: function(event, ui) {
            $j('#learn_req').val($j(this).sortable('toArray'));
            updateAriaPositions();
        }
    });
    $j('#learn_req').val($j("#sortable1").sortable('toArray'));

    $j("#sortable2").sortable({
        containment: "#learn_mods",
        scroll: false,
        connectWith: "#sortable1",
        cancel: cancelSelector,
        receive: makeReceiveHandler(false),
        update: function(event, ui) {
            $j('#learn_not_req').val($j(this).sortable('toArray'));
            updateAriaPositions();
        }
    });
    $j('#learn_not_req').val($j("#sortable2").sortable('toArray'));

    $j("#sortable3").sortable({
        containment: "#teach_mods",
        scroll: false,
        connectWith: "#sortable4",
        cancel: cancelSelector,
        receive: makeReceiveHandler(true),
        update: function(event, ui) {
            $j('#teach_req').val($j(this).sortable('toArray'));
            updateAriaPositions();
        }
    });
    $j('#teach_req').val($j("#sortable3").sortable('toArray'));

    $j("#sortable4").sortable({
        containment: "#teach_mods",
        scroll: false,
        connectWith: "#sortable3",
        cancel: cancelSelector,
        receive: makeReceiveHandler(false),
        update: function(event, ui) {
            $j('#teach_not_req').val($j(this).sortable('toArray'));
            updateAriaPositions();
        }
    });
    $j('#teach_not_req').val($j("#sortable4").sortable('toArray'));

    $j(".connectedSortable li").click(function() {
        $j(this).children("input").filter(function() {
            return $j(this).val() === "";
        }).toggle();
    });

    $j(".connectedSortable li input").click(function(event) {
        event.stopPropagation();
        // Do something
    });

    // Announce a message via the ARIA live region; brief clear ensures the
    // same text fires again if repeated.  The pending timer is cancelled
    // before scheduling a new one so rapid moves don't fire out of order.
    var announceTimer = null;
    function announce(msg) {
        var $live = $j('#module-reorder-announce');
        $live.text('');
        clearTimeout(announceTimer);
        announceTimer = setTimeout(function() { $live.text(msg); }, 50);
    }

    function updateAriaPositions() {
        $j('.connectedSortable').each(function() {
            var $items = $j(this).children('li');
            var size = $items.length;
            $items.each(function(idx) {
                $j(this).attr('aria-posinset', idx + 1).attr('aria-setsize', size);
            });
        });
    }

    function syncHiddenInputs() {
        $j('#learn_req').val($j('#sortable1').sortable('toArray'));
        $j('#learn_not_req').val($j('#sortable2').sortable('toArray'));
        $j('#teach_req').val($j('#sortable3').sortable('toArray'));
        $j('#teach_not_req').val($j('#sortable4').sortable('toArray'));
    }

    // Maps each sortable to its partner and the constraint blocking a cross-list
    // move (mirrors the logic in makeReceiveHandler above).
    var listMeta = {
        sortable1: { isRequired: true,  partner: '#sortable2', crossConstraint: 'required_locked',     crossMsg: 'This module must always be required.' },
        sortable2: { isRequired: false, partner: '#sortable1', crossConstraint: 'not_required_locked', crossMsg: 'This module cannot be required.' },
        sortable3: { isRequired: true,  partner: '#sortable4', crossConstraint: 'required_locked',     crossMsg: 'This module must always be required.' },
        sortable4: { isRequired: false, partner: '#sortable3', crossConstraint: 'not_required_locked', crossMsg: 'This module cannot be required.' }
    };

    updateAriaPositions();

    $j('.connectedSortable li').on('keydown', function(event) {
        var key = event.key;

        if (key === 'Enter' || key === ' ') {
            event.preventDefault();
            $j(this).children('input').filter(function() {
                return $j(this).val() === '';
            }).toggle();
            return;
        }

        if (key !== 'ArrowUp' && key !== 'ArrowDown') { return; }
        event.preventDefault();

        var $item = $j(this);
        var id    = $item.attr('id');
        var c     = constraints[id];

        if (c && c.position_locked) {
            announce($item.attr('aria-label') + ': position is fixed and cannot be changed.');
            return;
        }

        var $list = $item.closest('.connectedSortable');
        var meta  = listMeta[$list.attr('id')];
        var moved = false;

        if (key === 'ArrowUp') {
            var $prev = $item.prev('li');
            if ($prev.length) {
                $item.insertBefore($prev);
                moved = true;
            } else if (meta && !meta.isRequired) {
                if (c && c[meta.crossConstraint]) {
                    announce(meta.crossMsg);
                    return;
                }
                $item.detach().appendTo($j(meta.partner));
                $j(meta.partner).sortable('refresh');
                $list.sortable('refresh');
                moved = true;
            }
        } else {
            var $next = $item.next('li');
            if ($next.length) {
                $item.insertAfter($next);
                moved = true;
            } else if (meta && meta.isRequired) {
                if (c && c[meta.crossConstraint]) {
                    announce(meta.crossMsg);
                    return;
                }
                $item.detach().prependTo($j(meta.partner));
                $j(meta.partner).sortable('refresh');
                $list.sortable('refresh');
                moved = true;
            }
        }

        if (!moved) { return; }

        var $newList  = $item.closest('.connectedSortable');
        var newPos    = $item.index() + 1;
        var newSize   = $newList.children('li').length;
        var listLabel = $newList.attr('aria-label') || $newList.attr('id');

        updateAriaPositions();
        syncHiddenInputs();
        $item.focus();
        announce($item.attr('aria-label') + ': moved to position ' + newPos + ' of ' + newSize + ' in ' + listLabel + '.');
    });

    $j('.connectedSortable li input').on('keydown', function(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.stopPropagation();
        }
    });
});
