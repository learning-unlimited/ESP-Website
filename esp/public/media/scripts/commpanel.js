/*  Communications panel app    */

function set_step(base_div, step_name)
{
    //  console.log("Setting step in " + base_div + " to " + step_name);
    step_divs = $j("#" + base_div).children("div");
    for (var i = 0; i < step_divs.length; i++)
    {
        //  console.log(step_divs[i]);
        if (step_divs[i].id == step_name)
            $j("#" + step_divs[i].id).removeClass("commpanel_hidden");
        else
            $j("#" + step_divs[i].id).addClass("commpanel_hidden");
    }
}

function submit_basic_selection()
{
    //  Check that we at least have a list specified
    if ($j("input[name=base_list]:checked").length == 0)
    {
        alert("Please select a list of recipients to start with.");
        set_step("basic_step_container", "recipient_list_select");
        return false;
    }

    //  Submit the list information via POST
    $j("#form_basic_list").submit();
    return true;
}

function submit_combo_selection()
{
    //  Check that we at least have a list specified
    if (!($j("select[name=combo_base_list]").val()))
    {
        alert("Please select a list of recipients to start with.");
        set_step("combo_step_container", "starting_list_select");
        return false;
    }

    //  Submit the list information via POST
    $j("#form_combo_list").submit();
    return true;
}

function prepare_accordion(accordion_id, rb_selected)
{
    //  Show school/grade options for students, graduation year options for teachers
    if (rb_selected == "students")
    {
        $j("#" + accordion_id).children(".ui-accordion-header").eq(7).show();
        $j("#" + accordion_id).children(".ui-accordion-header").eq(8).show();
        $j("#" + accordion_id).children(".ui-accordion-header").eq(9).hide();
    }
    else if (rb_selected == "teachers")
    {
        $j("#" + accordion_id).children(".ui-accordion-header").eq(7).hide();
        $j("#" + accordion_id).children(".ui-accordion-header").eq(8).hide();
        $j("#" + accordion_id).children(".ui-accordion-header").eq(9).show();
    }
    else
    {
        $j("#" + accordion_id).children(".ui-accordion-header").eq(7).hide();
        $j("#" + accordion_id).children(".ui-accordion-header").eq(8).hide();
        $j("#" + accordion_id).children(".ui-accordion-header").eq(9).hide();
    }
}

function initialize() 
{
    //  Initialize the main tabs
    $j("#tabs").tabs();
    
    /*  Basic list tab  */
    
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
        set_step("basic_step_container", "recipient_list_select");
        $j("#recipient_type_name").html("Which set of " + rb_selected + " would you like to contact?");
        $j("#recipient_list_select").children("div").addClass("commpanel_hidden");
        $j("#recipient_list_select").children("div.step_header").removeClass("commpanel_hidden");
        $j("#recipient_list_options_" + rb_selected).removeClass("commpanel_hidden");
        //  console.log("Selected " + rb_selected);
        
        prepare_accordion("filter_accordion", rb_selected);
    });
    
    //  Handle changes in the recipient list radio buttons
    $j("input[name=base_list]").change(function () {
        set_step("basic_step_container", "recipient_filter_select");
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
    $j("#tab_select_basic").click(function () {set_step("basic_step_container", "recipient_type_select");});

    //  Prepare "back" buttons
    $j("a.recipient_step_button").button();
    $j("#recipient_list_back").click(function () {set_step("basic_step_container", "recipient_type_select");});
    $j("#recipient_filter_back").click(function () {set_step("basic_step_container", "recipient_list_select");});
    
    //  Prepare "next" buttons
    $j("#recipient_list_next").click(function () {set_step("basic_step_container", "recipient_filter_select");});
    
    //  Prepare "done" buttons
    $j("#recipient_list_done").click(submit_basic_selection);
    $j("#recipient_filter_done").click(submit_basic_selection);
    
    /*  Combination list tab    */
    
    //  Initialize the filtering options accordion
    $j("#combo_filter_accordion").accordion({
        autoHeight: false,
        collapsible: true,
        navigation: true
    });
    $j("#combo_filter_accordion").accordion("activate", false);
    
    //  Make AND/OR/NOT into buttons
    for (var i = 0; i < list_names.length; i++)
    {
        $j("#bool_options_" + list_names[i]).buttonset();
    }
    
    //  Make the ANDs turn off the ORs and vice versa
    for (var i = 0; i < list_names.length; i++)
    {
        with ({list_name: list_names[i]})
        {
            $j("input[name=checkbox_and_" + list_name + "]").change(function () {
                if ($j("input[name=checkbox_and_" + list_name + "]").prop("checked") 
                    && $j("input[name=checkbox_or_" + list_name + "]").prop("checked"))
                    $j("input[name=checkbox_or_" + list_name + "]").click();
            });
            $j("input[name=checkbox_or_" + list_name + "]").change(function () {
                if ($j("input[name=checkbox_and_" + list_name + "]").prop("checked") 
                    && $j("input[name=checkbox_or_" + list_name + "]").prop("checked"))
                    $j("input[name=checkbox_and_" + list_name + "]").click();
            });
        }
    }
    
    //  Handle step transitions
    $j("select[name=combo_base_list]").change(function () {
        set_step("combo_step_container", "combo_list_select");
        var list_selected = $j("select[name=combo_base_list]").val();
        $j("#combo_starting_list").html($j("#list_description_" + list_selected.substr(list_selected.indexOf(":") + 1)).html());
        //  TODO: Prepare filtering options based on starting list (students/teachers/other)
        //  prepare_accordion("combo_filter_accordion", rb_selected);
    });
    
    $j("#combo_base_done").change(function () {
        set_step("combo_step_container", "combo_list_select");
    });
    
    //  Handle the outer level tabs
    $j("#tab_select_combo").click(function () {set_step("combo_step_container", "starting_list_select");});
    
    //  Prepare "back" buttons
    $j("#combo_options_back").click(function () {set_step("combo_step_container", "starting_list_select");});
    $j("#combo_filter_back").click(function () {set_step("combo_step_container", "combo_list_select");});
    
    //  Prepare "next" buttons
    $j("#combo_base_next").click(function () {set_step("combo_step_container", "combo_list_select");});
    $j("#combo_options_next").click(function () {set_step("combo_step_container", "combo_filter_select");});
    
    //  Prepare "done" buttons
    $j("#combo_options_done").click(submit_combo_selection);
    $j("#combo_filter_done").click(submit_combo_selection);
}

$j(document).ready(initialize);

console.log("Loaded comm panel JS");
