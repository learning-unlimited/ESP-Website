$j(document).ready(function() {
    // Constraint metadata injected by the server (see admincore.py modules() view).
    // Keys are ProgramModuleObj IDs (as strings).
    // Values: {required_locked, not_required_locked, position_locked} — all booleans.
    // Mirrors the hard-override block that runs on every POST; the UI uses this
    // data to prevent illegal drags rather than silently undoing them on save.
    // Issue #3656.
    var constraints = JSON.parse(document.getElementById('module-constraints-data').textContent);

    // Mark every constrained module and collect their IDs for the cancel selector.
    var lockedSelectors = [];
    $j('.connectedSortable li').each(function() {
        var id = $j(this).attr('id');
        if (constraints.hasOwnProperty(id)) {
            $j(this).addClass('module-locked');
            lockedSelectors.push('#' + id);
        }
    });

    // Extend jQuery UI's default cancel selector so constrained modules cannot
    // be initiated as drag sources.
    var cancelSelector = 'input,textarea,button,select,option' +
        (lockedSelectors.length ? ',' + lockedSelectors.join(',') : '');

    // Reject cross-section drops for required-locked items as defense-in-depth.
    // (These modules are also non-draggable via cancelSelector, but this guard
    // ensures correctness if that ever changes.)
    function makeReceiveHandler(isRequiredList) {
        return function(event, ui) {
            var id = ui.item.attr('id');
            var c = constraints[id];
            if (!c) { return; }
            if (!isRequiredList && c.required_locked) {
                ui.sender.sortable('cancel');
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
