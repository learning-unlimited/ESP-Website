/*  Communications panel app    */

function set_step(step_name)
{
    //  console.log("Setting step to " + step_name);
    step_divs = $j("#step_container").children("div");
    for (var i = 0; i < step_divs.length; i++)
    {
        //  console.log(step_divs[i]);
        if (step_divs[i].id == step_name)
            $j("#" + step_divs[i].id).removeClass("commpanel_hidden");
        else
            $j("#" + step_divs[i].id).addClass("commpanel_hidden");
    }
}

function submit_list_selection()
{
    //  Check that we at least have a list specified
    if ($j("input[name=base_list]:checked").length == 0)
    {
        alert("Please select a list of recipients to start with.");
        set_step("recipient_list_select");
        return false;
    }

    //  Submit the list information via POST
    $j("#form_basic_list").submit();
    return true;
}

function initialize() 
{
    //  Initialize the main tabs
    $j("#tabs").tabs();
    
    //  Initialize the filtering options accordion
    $j("#filter_accordion").accordion({
        autoHeight: false,
        collapsible: true,
        navigation: true
    });
    $j("#filter_accordion").accordion("activate", false);
    
    //  Make the recipient type options look like buttons
    $j("#recipient_type_options").buttonset();

    //  Handle changes in the recipient type radio buttons
    $j("input[name=recipient_type]").click(function () {
        var rb_selected = $j("input[name=recipient_type]:checked").val();
        set_step("recipient_list_select");
        $j("#recipient_type_name").html(rb_selected);
        $j("#recipient_list_select").children("div").addClass("commpanel_hidden");
        $j("#recipient_list_options_" + rb_selected).removeClass("commpanel_hidden");
        //  console.log("Selected " + rb_selected);
    });
    
    //  Handle changes in the recipient list radio buttons
    $j("li.commpanel_list_entry").click(function () {
        set_step("recipient_filter_select");
        $j("#filter_current_list").html($j("#label_" + $j("input[name=base_list]:checked").val()).html());
    });
    
    //  Handle clicks on show/hide e-mail list links
    $j("li.commpanel_show_all").click(function () {
        $j("li.commpanel_list_entry").removeClass("commpanel_hidden");
        $j("li.commpanel_show_all").addClass("commpanel_hidden");
        $j("li.commpanel_show_preferred").removeClass("commpanel_hidden");
    });
    $j("li.commpanel_show_preferred").click(function () {
        $j("li.commpanel_list_entry").addClass("commpanel_hidden");
        $j("li.commpanel_list_entry.commpanel_list_preferred").removeClass("commpanel_hidden");
        $j("li.commpanel_show_all").removeClass("commpanel_hidden");
        $j("li.commpanel_show_preferred").addClass("commpanel_hidden");
    });
    $j("#recipient_list_select").children("div").addClass("commpanel_hidden");

    //  Handle the outer level tabs
    $j("#tab_select_basic").click(function () {set_step("recipient_type_select");});

    //  Prepare "back" buttons
    $j("#recipient_list_back").button();
    $j("#recipient_list_back").click(function () {set_step("recipient_type_select");});
    $j("#recipient_filter_back").button();
    $j("#recipient_filter_back").click(function () {set_step("recipient_list_select");});
    
    //  Prepare "done" buttons
    $j("#recipient_list_done").button();
    $j("#recipient_list_done").click(submit_list_selection);
    $j("#recipient_filter_done").button();
    $j("#recipient_filter_done").click(submit_list_selection);
}

$j(document).ready(initialize);

console.log("Loaded comm panel JS");
