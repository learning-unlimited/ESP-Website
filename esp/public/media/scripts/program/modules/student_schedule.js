//  Behavior for the inline student schedule fragment.
//
//  The schedule fragment is re-rendered by the ajax_schedule view, which is
//  invoked by name in ajax_tools.js.

//  Attach the removal confirmation dialogs to the remove links currently in the
//  document.  The dialogs live inside the schedule fragment, so this has to be
//  re-run every time the fragment is replaced.
function setup_remove_confirmation()
{
    //  Create two dialog boxes with two different warning messages,
    //  one that appears when you try to remove an enrolled class,
    //  and another that appears when you try removing a non-enrolled class.
    //  autoOpen: false makes it so that the dialog boxes don't appear on page load.
    $j("div.remove-confirm").dialog({
        resizable: false,
        modal: true,
        autoOpen: false,
        closeOnEscape: false
    });

    //  When clicking any remove link, handle the event here rather than immediately removing the class.
    //  Display a warning dialog box, and give the user an option to confirm the removal or cancel it.
    $j("a.remove").click(function(eventObject) {
        //  The hyperlink click is always cancelled at first.
        //  If the user confirms the removal,
        //  the clearslot link is followed, and the class is removed.
        eventObject.preventDefault();
        var $a_remove_tag = $j(this);
        var cls_code = $j(this).attr("data-sec-code");
        //  "enrolled" for enrolled classes, "applied" for non-enrolled classes
        var remove_type = $j(this).attr("data-remove-type");
        $j("#" + remove_type + "-remove-confirm").dialog("option", "title", "Remove class " + cls_code + "?").dialog("option", "buttons", {
            "Remove class": function() {
                $j(this).dialog("close");
                window.location.replace($a_remove_tag.attr("href"));
            },
            "Cancel": function() {
                $j(this).dialog("close");
            }
        }).dialog("open");
    });
}

//  Applied after the ajax_schedule view replaces the schedule markup.
//  options.reg_open:     whether student registration is currently open
//  options.onsite_local: whether this is an onsite session, in which
//                        case the removal confirmation dialogs are skipped
function apply_student_schedule(options)
{
    options = options || {};

    //  Show or hide the catalog's "add class" buttons to match whether
    //  registration is open.
    $j(".addbutton").css({visibility: options.reg_open ? "visible" : "hidden"});

    if (!options.onsite_local)
    {
        $j(setup_remove_confirmation);
    }
}

//  Only registered when this page also loaded the Ajax tools
if (typeof register_handler === "function")
{
    register_handler("student_schedule", apply_student_schedule);
}
