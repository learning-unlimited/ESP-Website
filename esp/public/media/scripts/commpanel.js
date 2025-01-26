/*  Communications panel app    */

function set_step(base_div, step_name)
{
    //  Special case for the basic list step, which needs to clear the buttons
    if ((base_div == "basic_step_container") && (step_name == "recipient_type_select"))
    {
        $j("input[name=recipient_type]").prop("checked", false);
        $j("input[name=recipient_type]").button("refresh");
    }

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

function submit_prev_selection()
{
    if (!($j("input[name=msgreq_id]").val()))
    {
        alert("Please select a previous message to start with.");
        return false;
    }
    $j("#form_previous").submit();
    return true;
}

function prepare_accordion(rb_selected)
{
    $j("#filter_accordion").children(".ui-accordion-header:not(.any)").hide();
    
    //  Show school/grade options for students, graduation year options for teachers
    if (rb_selected.toLowerCase().substr(0, 7) == "student")
    {
        $j("#filter_accordion").children(".ui-accordion-header.student").show();
    }
    else if (rb_selected.toLowerCase().substr(0, 7) == "teacher")
    {
        $j("#filter_accordion").children(".ui-accordion-header.teacher").show();
    }
    else // otherwise, show all options
    {
        $j("#filter_accordion").children(".ui-accordion-header").show();
    }
}

var msgreq_data;

function msgreq_select_item(event, ui)
{
    last_select_event = [event, ui];
    var msgreq_id = ui.item.value;
    $j("input[name=msgreq_id]").val(ui.item.label);

    var target_div = $j("#msgreq_info_area");
    var msgreq = msgreq_data[msgreq_id];
    target_div.html("");
    var md = msgreq.processed_by;
    var md_str;
    if (md)
        md_str = md[1] + "/" + md[2] + "/" + md[0];
    else
        md_str = "Not sent";
    var inner_div1 = $j("<div/>").html("<b>Selected Message</b>");
    var inner_div2 = $j("<ul><li><b>Subject</b>: " + msgreq.subject + "</li><li><b>Sender</b>: " + msgreq.creator__first_name + " " + msgreq.creator__last_name + " (" + msgreq.creator__username + ")</li><li><b>Send Date</b>: " + md_str + "</li><li><b>Recipients</b>: " + msgreq.recipients__useful_name + "</li></ul>");
    var inner_div3 = $j("<div class=\"email_contents\">" + msgreq.msgtext.replace(/\n/g, "<br />") + "</div><br />");
    target_div.append(inner_div1);
    target_div.append(inner_div2);
    target_div.append(inner_div3);
}

function populate_get()
{
    //  Populate fields with GET parameters
    var items = location.search.substr(1).split("&").filter(Boolean);
    for (var index = 0; index < items.length; index++) {
        var key_val = items[index].split("=");
        var field = $j("#tabs [name=" + key_val[0] + "]");
        if(field.length >= 1){
            switch (field[0].type) {
                case 'checkbox':
                    // don't need a value for a checkbox, just check it
                    field[0].checked = true;
                    break;
                default:
                    if(key_val.length == 2){
                        field.val(key_val[1].split(","));
                        if(key_val[0] == "recipient_type") recipient_type_change(clear = false);
                    } else {
                        // skip it and keep going if a value wasn't specified
                        break;
                    }
            }
        }
    }
}

function clear_filters()
{
    //  Remove any existing data in the "user filtering options" part of a comm panel form
    var $form = $j("#filter_accordion");
    // Don't set the grade fields if we are in the combo list form
    var set_grade = $form.parent().attr('id') != "combo_filter_accordion" && window.location.href.includes("commpanel");
    var form_fields = $form.find(':input');
    form_fields.each(function(i, form_field) {
        if(set_grade && form_field.name == "grade_min" && $j("select[name=recipient_type]").val() == "Student"){
            $j(form_field).val(program_grade_min);
        } else if(set_grade && form_field.name == "grade_max" && $j("select[name=recipient_type]").val() == "Student"){
            $j(form_field).val(program_grade_max);
        } else{
            switch (form_field.type) {
                case 'checkbox':
                    form_field.checked = false;
                    break;
                case 'radio':
                    form_field.checked = false;
                    break;
                default:
                    $j(form_field).val('');
            }
        }
    });
    $j("#filter_accordion").accordion("option", "active", false);
}

function move_filters(wrapper_name)
{
    clear_filters();
    $j("#filter_accordion").detach().appendTo('#'+wrapper_name)
    $j("#filter_accordion").accordion("option", "active", false);
}

function set_field(form_name, field_name, value)
{
    var form = $j("#"+form_name)[0];
    var form_field = $j(form).find(':input[name=' + field_name + ']')[0];
    $j(form_field).val(value);
}

function initialize()
{
    //  Initialize the main tabs
    $j("#tabs").tabs();

    /*  Basic list tab  */

    //  Initialize the filtering options accordion
    $j("#filter_accordion").accordion({
        heightStyle: "content",
        collapsible: true,
        active: false,
    });

    //  Handle changes in the recipient type
    recipient_type_change = function (clear = true) {
        var rb_selected = $j("select[name=recipient_type]").val();
        $j("#recipient_type_name").html("Which set of <b>" + $j("option[value=" + rb_selected +"]").html() + "</b> would you like to contact?");
        $j("#recipient_list_select").children("div").addClass("commpanel_hidden");
        $j("#recipient_list_select").children("div.step_header").removeClass("commpanel_hidden");
        $j("#recipient_list_options_" + rb_selected).removeClass("commpanel_hidden");
        $j(".sendto_fn_select").addClass("commpanel_hidden");
        $j("." + rb_selected + ".sendto_fn_select").removeClass("commpanel_hidden");
        if(clear) {
            $j("[name=base_list]").prop('checked', false); // Clear the selected radio button
            clear_filters(); // Clear the filters
        }
        prepare_accordion(rb_selected);
    }
    $j("select[name=recipient_type]").on('change', recipient_type_change);
    $j("#recipient_type_next").on('click', function () {
        set_step("basic_step_container", "recipient_list_select");
        return false;
    });

    //  Handle clicks on show/hide email list links
    $j("button.commpanel_show_all").on('click', function () {
        $j("li.commpanel_list_entry").removeClass("commpanel_hidden");
        $j("button.commpanel_show_all").addClass("commpanel_hidden");
        $j("button.commpanel_show_preferred").removeClass("commpanel_hidden");
        return false;
    });
    $j("button.commpanel_show_preferred").on('click', function () {
        $j("li.commpanel_list_entry").addClass("commpanel_hidden");
        $j("li.commpanel_list_entry.commpanel_list_preferred").removeClass("commpanel_hidden");
        $j("button.commpanel_show_all").removeClass("commpanel_hidden");
        $j("button.commpanel_show_preferred").addClass("commpanel_hidden");
        return false;
    });
    $j("#recipient_list_select").children("div").addClass("commpanel_hidden");

    //  Handle the outer level tabs
    $j("#tab_select_basic").on('click', function () {
        move_filters("base_filter_accordion");
        recipient_type_change();
        set_step("basic_step_container", "recipient_type_select"); return false;
    });

    //  Prepare "back" buttons
    $j("#recipient_list_back").on('click', function () {set_step("basic_step_container", "recipient_type_select"); return false;});
    $j("#recipient_filter_back").on('click', function () {set_step("basic_step_container", "recipient_list_select"); return false;});

    //  Prepare "next" buttons
    $j("#recipient_list_next").on('click', function () {set_step("basic_step_container", "recipient_filter_select"); return false;});

    //  Prepare "done" buttons
    $j("#recipient_list_done").on('click', submit_basic_selection);
    $j("#recipient_filter_done").on('click', submit_basic_selection);
    $j("#recipient_filter_checklist").on('click', function () {
        set_field("form_basic_list", "use_checklist", "1");
        return submit_basic_selection();
    });

    /*  Combination list tab    */
    //  Make AND/OR/NOT into buttons
    for (var i = 0; i < list_names.length; i++)
    {
        $j("#bool_options_" + list_names[i]).buttonset();
    }

    for (var i = 0; i < list_names.length; i++)
    {
        with ({list_name: list_names[i]})
        {
            //  Make the ANDs turn off the ORs and vice versa
            $j("input[name=checkbox_and_" + list_name + "]").on('change', function () {
                if ($j("input[name=checkbox_and_" + list_name + "]").prop("checked")
                    && $j("input[name=checkbox_or_" + list_name + "]").prop("checked"))
                    $j("input[name=checkbox_or_" + list_name + "]").click();
            });
            $j("input[name=checkbox_or_" + list_name + "]").on('change', function () {
                if ($j("input[name=checkbox_and_" + list_name + "]").prop("checked")
                    && $j("input[name=checkbox_or_" + list_name + "]").prop("checked"))
                    $j("input[name=checkbox_and_" + list_name + "]").click();
            });
            //  NOT can't be selected by itself
            $j("input[name=checkbox_not_" + list_name + "]").on('change', function () {
                if ($j("input[name=checkbox_not_" + list_name + "]").prop("checked")
                    && !$j("input[name=checkbox_and_" + list_name + "]").prop("checked")
                    && !$j("input[name=checkbox_or_" + list_name + "]").prop("checked"))
                    $j("input[name=checkbox_and_" + list_name + "]").click();
            });
        }
    }

    //  Handle step transitions
    combo_base_list_change = function () {
        clear_filters();
        var list_selected = $j("select[name=combo_base_list]").val();
        $j("#combo_starting_list").html($j("#list_description_" + list_selected.substr(list_selected.indexOf(":") + 1)).html());
        $j("#tab_combo .sendto_fn_select").hide();
        try {
            $j("#tab_combo .sendto_fn_select." + list_selected.split(":")[0]).show();
        } catch(e){}
        //  TODO: Prepare filtering options based on choice of starting list (students/teachers/other)
        prepare_accordion("combo");
    }
    combo_base_list_change();
    $j("select[name=combo_base_list]").on('change', combo_base_list_change);

    $j("#combo_base_done").on('change', function () {
        set_step("combo_step_container", "combo_list_select");
    });

    //  Handle the outer level tabs
    $j("#tab_select_combo").on('click', function () {
        move_filters("combo_filter_accordion");
        prepare_accordion("combo");
        $j("[name=base_list]").prop('checked', false);
        set_step("combo_step_container", "starting_list_select"); return false;
    });

    //  Prepare "back" buttons
    $j("#combo_options_back").on('click', function () {set_step("combo_step_container", "starting_list_select"); return false;});
    $j("#combo_filter_back").on('click', function () {set_step("combo_step_container", "combo_list_select"); return false;});

    //  Prepare "next" buttons
    $j("#combo_base_next").on('click', function(){
        combo_base_list_change();
        set_step("combo_step_container", "combo_list_select");
        return false;
    });
    $j("#combo_options_next").on('click', function () {set_step("combo_step_container", "combo_filter_select"); return false;});

    //  Prepare "done" buttons
    $j("#combo_options_done").on('click', submit_combo_selection);
    $j("#combo_filter_checklist").on('click', function () {
        set_field("form_combo_list", "use_checklist", "1");
        return submit_combo_selection();
    });
    $j("#combo_filter_done").on('click', submit_combo_selection);

    /*  Previous emails tab    */

    //  Set up message request autocomplete
    msgreq_data = json_fetch(["message_requests"], function (result_data) {
        msgreq_data = result_data.message_requests;
        var msgreq_strings = [];
        for (var id in result_data.message_requests)
        {
            msgreq_strings.push({label: result_data.message_requests[id].subject, value: id});
        }

        $j("#msgreq_selector").autocomplete({
            source: msgreq_strings,
            select: msgreq_select_item
        });
    }, null, function(jqXHR, status, errorThrown) {
        if (errorThrown == "NOT FOUND") {
            alert("Error: JSON view not found.  Please enable the JSON Data Module for this program.");
        }
    });

    //  Handle submit button
    $j("#prev_select_done").on('click', submit_prev_selection);

    populate_get();
    recipient_type_change(clear = false);
}

$j(document).ready(initialize);

console.log("Loaded comm panel JS");
