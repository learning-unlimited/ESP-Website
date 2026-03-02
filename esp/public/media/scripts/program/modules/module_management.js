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
});
