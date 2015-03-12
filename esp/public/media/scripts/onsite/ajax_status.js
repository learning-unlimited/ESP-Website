/*  
    Javascript code for the onsite check-in interface.
    
    This could easily be merged into a more general library for client-side admin views,
    since it fetches a lot of data from the server and builds data structures in the
    browser which are kind of like a simplified version of our server-side DB schema.
*/

//  This is the primary data structure for all received data.
var data = {};
var minMinutesToHideTimeSlot = 20;

//  Some parameters for things that can be customized in the future.
var settings = {
    checkin_colors: false,
    show_full_classes: true,
    override_full: false,
    disable_grade_filter: false,
    compact_classes: true,
    categories_to_display: {}
};

/*  Ajax status flags
    We request multiple chunks of data from the server concurrently
    and have to wait for all of them to arrive before we populate the
    internal data structures.
*/

//  This is a set of flags for whether each batch of JSON data has arrived
var data_status = {
    catalog_received: false,
    enrollment_received: false,
    checkins_received: false,
    counts_received: false,
    rooms_received: false,
    students_received: false
};

//  This function resets all the flags
function reset_status()
{
    data_status.catalog_received = false;
    data_status.enrollment_received = false;
    data_status.checkins_received = false;
    data_status.counts_received = false;
    data_status.rooms_received = false;
    data_status.students_received = false;
}

//  This function only returns true if all flags have been set
//  (i.e. we received all necessary data)
function check_status()
{
    if (!data_status.catalog_received)
        return false;
    if (!data_status.enrollment_received)
        return false;
    if (!data_status.checkins_received)
        return false;
    if (!data_status.counts_received)
        return false;
    if (!data_status.rooms_received)
        return false;
    if (!data_status.students_received)
        return false;
        
    return true;
}

//  This is a state variable.
var state = {
    status: data_status,
    display_mode: "status",
    student_id: null,
    student_schedule: null,
    last_event: null
};

/*  Ajax handler functions
    These save the received data and, if they're the last one being called,
    call handle_completed() to go through all of the data.  */

function handle_catalog(new_data, text_status, jqxhr)
{
    data.catalog = new_data;
    data_status.catalog_received = true;
    if (check_status())
        handle_completed();
}

function handle_counts(new_data, text_status, jqxhr)
{
    data.counts = new_data;
    data_status.counts_received = true;
    if (check_status())
        handle_completed();
}

function handle_enrollment(new_data, text_status, jqxhr)
{
    data.enrollments = new_data;
    data_status.enrollment_received = true;
    if (check_status())
        handle_completed();
}

function handle_checkins(new_data, text_status, jqxhr)
{
    data.checkins = new_data;
    data_status.checkins_received = true;
    if (check_status())
        handle_completed();
}

function handle_rooms(new_data, text_status, jqxhr)
{
    data.rooms = new_data;
    data_status.rooms_received = true;
    if (check_status())
        handle_completed();
}

function handle_students(new_data, text_status, jqxhr)
{
    data.students_list = new_data;
    data_status.students_received = true;
    if (check_status())
        handle_completed();
}

function handle_compact_classes()
{
    var div = $j('div[id=compact-classes-body]');
    var val = settings.compact_classes;
    //  This line would make the entire class description appear inline
    //  instead of just the title.
    //  div.toggleClass( "compact-classes" , val);
}

//  I wonder why this variable is necessary...
var last_settings_event;
function handle_settings_change(event)
{
    last_settings_event = event;
    setup_settings();
    render_table(state.display_mode, state.student_id);
    handle_compact_classes();
    update_checkboxes();
}

function setup_settings()
{
    $j("#hide_full_control").unbind("change");
    $j("#override_control").unbind("change");
    $j("#grade_limits_control").unbind("change");
    $j("#compact_classes").unbind("change");
    $j("#show_closed_reg").unbind("change");
    $j("#hide_past_time_blocks").unbind("change");


    //  Apply settings
    settings.show_full_classes = $j("#hide_full_control").prop("checked");
    settings.override_full = $j("#override_control").prop("checked");
    settings.disable_grade_filter = $j("#grade_limits_control").prop("checked");
    settings.compact_classes = $j("#compact_classes").prop("checked");
    settings.show_closed_reg = $j("#show_closed_reg").prop("checked");
    settings.hide_past_time_blocks = $j("#hide_past_time_blocks").prop("checked");

    $j("#hide_full_control").change(handle_settings_change);
    $j("#override_control").change(handle_settings_change);
    $j("#grade_limits_control").change(handle_settings_change);
    $j("#compact_classes").change(handle_settings_change);
    $j("#show_closed_reg").change(handle_settings_change);
    $j("#hide_past_time_blocks").change(handle_settings_change);
}

/*  Event handlers  */

function show_loading_box()
{
    var loading_box = $j("<div/>").attr("id", "loading_box");
    loading_box.html("Loading...");
    loading_box.dialog({
        autoOpen: true,
        modal: false
    });
}

function hide_loading_box()
{
    $j("#loading_box").dialog("close");
}

function print_schedule()
{
    printer_name = $j("#printer_selector").attr("value");
    printing_url = program_base_url + "printschedule_status";
    var student_data = { 'user' : state.student_id }
    if (printer_name)
        student_data.printer = printer_name
    result = $j.ajax({
        url: printing_url,
        data: student_data,
        async: false
    });
    add_message(JSON.parse(result.responseText).message);
}

function add_message(msg, cls)
{
    if (!cls)
        $j("#messages").append($j("<div/>").addClass("message").html(msg));
    else
        $j("#messages").append($j("<div/>").addClass(cls).html(msg));
    $j("#messages").prop("scrollTop", $j("#messages").prop("scrollHeight"));
}

function update_checkboxes()
{
    $j(".section_highlight").removeClass("section_highlight");
    $j(".section_conflict").removeClass("section_conflict");
    $j(".student_enrolled").removeClass("student_enrolled");
    $j(".classchange_checkbox").removeAttr("checked");
    $j(".classchange_checkbox").removeAttr("disabled");
    $j(".classchange_checkbox").unbind("change");
    data.conflicts = {};
    
    //  Gray out checkboxes for full classes.  Checkboxes for non-full classes trigger
    //  the handle_checkbox() function when they are clicked on.
    for (var ts_id in data.timeslots)
    {
        for (var i in data.timeslots[ts_id].sections)
        {
            var section = data.sections[data.timeslots[ts_id].sections[i]];
            var studentcheckbox = $j("#classchange_" + section.id + "_" + state.student_id + "_" + ts_id);
            studentcheckbox.hover(check_conflicts, clear_conflicts);
            //  Disable the checkbox if the class is full, unless we are overriding that
            if ((section.num_students_enrolled >= section.capacity) && (!(settings.override_full))) 
            {
                studentcheckbox.attr("disabled", "disabled");
            } 
            else if (section.registration_status != 0) 
            {
		      studentcheckbox.attr("disabled", "disabled");
            } 
            else if (data.classes[section.class_id].category__id == open_class_category.id)
            {
                studentcheckbox.attr("disabled", "disabled");
            }
            else 
            {
                studentcheckbox.change(handle_checkbox);
            }
        }
    }
    
    for (var i in state.student_schedule)
    {
        var section = data.sections[state.student_schedule[i]];
        for (var j in section.timeslots)
        {
            var studentcheckbox = $j("#classchange_" + section.id + "_" + state.student_id + "_" + section.timeslots[j]);
            var section_elem = $j("#section_" + section.id + "_" + section.timeslots[j]);
            section_elem.addClass("student_enrolled");
            var section_col = section_elem.parent();
            section_elem.detach();
            section_col.prepend(section_elem);
            studentcheckbox.attr("checked", "checked");
            studentcheckbox.removeAttr("disabled");
            studentcheckbox.change(handle_checkbox);
        }
    }

    //  console.log("Refreshed checkboxes");
}

function handle_schedule_response(new_data, text_status, jqxhr)
{
    data.students[new_data.user].grade = new_data.user_grade
    //  Save the new schedule
    state.student_schedule = new_data.sections;
    state.student_schedule.sort();
    //  console.log("Updated schedule for student " + new_data.user);
    for (var i in new_data.messages)
    {
        add_message(new_data.messages[i]);
    }
    
    //  Update the table if possible
    if (check_status())
        update_checkboxes();
}

//  Set the currently active student
function set_current_student(student_id)
{
    if (student_id)
    {
        state.student_id = student_id;
        state.display_mode = "classchange";
        var schedule_resp = $j.ajax({
            url: program_base_url + "get_schedule_json?user=" + student_id,
            async: false,
            success: handle_schedule_response
        });
        render_classchange_table(student_id);
        $j("#status_switch").removeAttr("disabled");
        $j("#schedule_print").removeAttr("disabled");
        $j("#status_switch").unbind("click");
        $j("#schedule_print").unbind("click");
        $j("#status_switch").click(function () {set_current_student(null);});
        $j("#schedule_print").click(function () {print_schedule();});
    }
    else
    {
        state.student_id = null;
        state.display_mode = "status";
        render_status_table();
        $j("#student_selector").attr("value", "");
        $j("#status_switch").attr("disabled", "disabled");
        $j("#schedule_print").attr("disabled", "disabled");
    }
}

var last_conflict_event = null;
function check_conflicts(event)
{
    last_conflict_event = event;
    
    var event_info = event.target.id.split("_");
    var section_id = event_info[1];
    var student_id = event_info[2];
    var timeslot_id = event_info[3];
    var conflict_highlighted_list = [];
    var timeslot_list = [];

    //  Highlight this and the other timeslots of this class.
    for (var i in data.sections[section_id].timeslots)
    {
        var target_div_id = "section_" + section_id + "_" + data.sections[section_id].timeslots[i];
        $j("#" + target_div_id).addClass("section_highlight");
        conflict_highlighted_list.push(target_div_id);
        timeslot_list.push();
        
        //  Check to see if they are in any other classes at the same time; highlight those and register the conflicts.
        for (var j in state.student_schedule)
        {
            //  Move along if you're enrolled in the class already; that's no conflict.
            if (state.student_schedule[j] == section_id)
                continue;
                
            if (data.sections[state.student_schedule[j]].timeslots.indexOf(data.sections[section_id].timeslots[i]) != -1)
            {
                for (var k in data.sections[state.student_schedule[j]].timeslots)
                {
                    var conflict_div_id = "section_" + state.student_schedule[j] + "_" + data.sections[state.student_schedule[j]].timeslots[k];
                    $j("#" + conflict_div_id).addClass("section_conflict");
                    conflict_highlighted_list.push(conflict_div_id);
                    //  console.log("Detected conflict between " + section_id + " and " + state.student_schedule[j] + " at " + data.sections[state.student_schedule[j]].timeslots[k]);
                }
            }
        }
    }
    
    data.conflicts[event.target.id] = conflict_highlighted_list;
    //  console.log("Hovering over section " +  + " at time " + );
}

function clear_conflicts(event)
{
    for (var i in data.conflicts[event.target.id])
    {
        $j("#" + data.conflicts[event.target.id][i]).removeClass("section_highlight");
        $j("#" + data.conflicts[event.target.id][i]).removeClass("section_conflict");
        //  console.log("Un-highlighted " + data.conflicts[event.target.id][i]);
    }
    delete data.conflicts[event.target.id];
}

//  Add a student to a class
function add_student(student_id, section_id, size_override)
{
    if (state.student_id != student_id)
    {
        //  console.log("Warning: student " + student_id + " is not currently selected for updates.");
    }
        
    var new_sections = state.student_schedule;
    section_id = parseInt(section_id);
    
    //  TODO: Remove any conflicting classes [???]
    
    //  console.log("add_student: Updated sections are " + new_sections.toString());
    
    //  Add desired section to list if it isn't already there
    if (new_sections.indexOf(section_id) == -1)
        new_sections.push(section_id);
    else
    {
        //  console.log("Section " + section_id + " already found in current schedule");
    }
    
    //  Commit changes to server
    var schedule_resp = $j.ajax({
        url: program_base_url + "update_schedule_json?user=" + student_id + "&sections=[" + new_sections.toString() + "]&override=" + size_override,
        async: false,
        success: handle_schedule_response
    });
}

//  Remove a student from a class
function remove_student(student_id, section_id)
{
    if (state.student_id != student_id)
    {
        //  console.log("Warning: student " + student_id + " is not currently selected for updates.");
    }
        
    var new_sections = state.student_schedule;
    section_id = parseInt(section_id);
    
    //  Remove desired section from list if it's there
    if (new_sections.indexOf(section_id) != -1)
        new_sections = new_sections.slice(0, new_sections.indexOf(section_id)).concat(new_sections.slice(new_sections.indexOf(section_id) + 1));
    else
    {
        //  console.log("Section " + section_id + " not found in current schedule");
    }
 
    //  console.log("remove_student: Updated sections are " + new_sections.toString());
   
    //  Commit changes to server
    var schedule_resp = $j.ajax({
        url: program_base_url + "update_schedule_json?user=" + student_id + "&sections=[" + new_sections.toString() + "]",
        async: false,
        success: handle_schedule_response
    });
}

//  Figure out what to do when one of the checkboxes is hit.
//  It could be either "on" or "off".
function handle_checkbox(event)
{
    //  The checkbox ids are of the form classchange_[section id]_[student id]_[timeslot id], e.g. classchange_4100_55502_475
    var target_info = event.target.id.split("_");
    var cur_grade = data.students[state.student_id].grade;
    var target_section = data.sections[parseInt(target_info[1])];
    
    if (event.target.checked)
    {
        //  console.log("Handling CHECKING of " + event.target.id);
        
        //  Check for conflicts
        var verified = true;
        if (data.conflicts[event.target.id])
        {
            var conflicted_sections_list = [];
            for (var i in data.conflicts[event.target.id])
            {
                var section_conflict_id = data.conflicts[event.target.id][i].split("_")[1];
                if ((section_conflict_id != target_info[1]) && (conflicted_sections_list.indexOf(section_conflict_id) == -1))
                    conflicted_sections_list.push(section_conflict_id);
            }
            if (conflicted_sections_list.length > 0)
            {
                verified = confirm("Registering for this class will remove the student from " + conflicted_sections_list.length + " other class[es].  Are you sure?");
            }
        }
        
        //  Check grade
        if (verified)
        {
            if ((cur_grade < target_section.grade_min) || (cur_grade > target_section.grade_max))
            {
                verified = confirm("This class is for grades " + target_section.grade_min + "--" + target_section.grade_max + ", but the current student is in grade " + cur_grade + ".  Are you sure you want to register them for this class?");
            }
        }
        
        //  Check size override
        var size_override = false;
        if ((verified) && (settings.override_full))
        {
            if (target_section.num_students_enrolled >= target_section.capacity)
            {
                verified = confirm("This class is full or oversubscribed (" + target_section.num_students_enrolled + " students, " + target_section.capacity + " spots).  Are you sure you want to register the student?");
                if (verified)
                    size_override = true;
            }
        }
        
        //  Send request to the server if 
        if (verified)
            add_student(target_info[2], target_info[1], size_override);
        else
        {
            $j("#" + event.target.id).removeAttr("checked");
        }
    }
    else
    {
        //  console.log("Handling UN-CHECKING of " + event.target.id);
        remove_student(target_info[2], target_info[1]);
    }
}

var last_select_event = null;
function autocomplete_select_item(event, ui)
{
    last_select_event = [event, ui];
    event.preventDefault();
    var student_id = ui.item.value;
    
    //  Refresh the table of checkboxes for the newly selected student.
    if ((student_id > 0) && (student_id < 99999999))
        set_current_student(parseInt(student_id));
    else
    {
        //  console.log("Invalid student selected: " + s);
    }
}

function setup_autocomplete()
{
    var student_strings = [];
    for (var i in data.students) {
        var student = data.students[i];
        var studentItem = {};
        studentItem.value = i;
        studentItem.label = student.first_name + " " + student.last_name + " (" + i + ")";
        
        student_strings.push(studentItem);
    }

    $j("#student_selector").autocomplete({
        source: student_strings,
        select: autocomplete_select_item,
        focus: function( event, ui ) {
            $j( "#student_selector" ).val( ui.item.label );
            return false;
        },
    });
}

function clear_table()
{
    $j(".section").removeClass("section_highlight");
    $j(".section").removeClass("section_conflict");
    $j(".section").removeClass("student_enrolled");

    for (var ts_id in data.timeslots)
    {
        var div_name = "timeslot_" + ts_id;
        var ts_div = $j("#" + div_name);
        
        ts_div.html("");
    }
}

/*  This function turns the data structure populated by handle_completed() (below)
    into a table displaying the enrollment and check-in status of all sections. 
    Additional features are controlled by display_mode and student_id.  */
var last_hover_event = null;
function render_table(display_mode, student_id)
{
    render_category_options();
    clear_table();
    for (var ts_id in data.timeslots)
    {
        var timeSlotHeader = data.timeslots[ts_id].label;

        if (settings.hide_past_time_blocks) 
        {
            var startTimeMillis = data.timeslots[ts_id].startTimeMillis;
            //excludes timeslots that have a start time 20 minutes prior to the current time
            var differenceInMinutes = Math.floor((Date.now() - startTimeMillis)/60000);

            if(differenceInMinutes > minMinutesToHideTimeSlot) 
            {
                continue;
            }
        }

        var div_name = "timeslot_" + ts_id;
        var ts_div = $j("#" + div_name);
        
        ts_div.append($j("<div/>").addClass("timeslot_header").html(timeSlotHeader));
        var classes_div = $j("<div/>");
        for (var i in data.timeslots[ts_id].sections)
        {
            var section = data.sections[data.timeslots[ts_id].sections[i]];
            var parent_class = data.classes[section.class_id];
            
            var new_div = $j("<div/>").addClass("section");
            new_div.addClass("section_category_" + parent_class.category__id);
            
            if (display_mode == "classchange")
            {
                var studentcheckbox = $j("<input/>").attr("type", "checkbox").attr("id", "classchange_" + section.id + "_" + student_id + "_" + ts_id).addClass("classchange_checkbox");
                //  Parameters of these checkboxes will be set in the update_checkboxes() function above
                new_div.append(studentcheckbox);
            }
            
            //  Hide the class if the current student is outside the grade range (and we are filtering by grade)
            if ((display_mode == "classchange") && ((section.grade_min > data.students[student_id].grade) || (section.grade_max < data.students[student_id].grade)))
            {
                if ((!(settings.disable_grade_filter)) && (data.students[student_id].sections.indexOf(section.id) == -1))
                    new_div.addClass("section_hidden");
            }
            
            //  Hide the class if it's full (and we are filtering full classes)
            if (section.num_students_enrolled >= section.capacity)
            {
                if ((!(settings.show_full_classes)) && ((display_mode == "status") || (data.students[student_id].sections.indexOf(section.id) == -1)))
                    new_div.addClass("section_hidden");
            }
            
	    //  Hide the class if its registration is closed (and we're not showing closed classes)
	    if ((!(settings.show_closed_reg)) && (section.registration_status != 0))
                new_div.addClass("section_hidden");
            
            new_div.append($j("<span/>").addClass("emailcode").html(section.emailcode));
            new_div.append($j("<span/>").addClass("room").html(section.rooms));
            //  TODO: make this snap to the right reliably
            new_div.append($j("<span/>").addClass("studentcounts").attr("id", "studentcounts_" + section.id).html(section.num_students_checked_in.toString() + "/" + section.num_students_enrolled + "/" + section.capacity));
            
            // Show the class title if we're not in compact mode
            if (!settings.compact_classes)
            {
                new_div.append($j("<div/>").addClass("title").html(section.title));
            }
            
            //  Create a tooltip with more information about the class
            new_div.addClass("tooltip");
            var tooltip_div = $j("<span/>").addClass("tooltip_hover").attr("id", div_name);
            var class_data = data.classes[section.class_id];
            var short_data = section.title + " - Grades " + class_data.grade_min.toString() + "--" + class_data.grade_max.toString();
            if(class_data.hardness_rating) short_data = class_data.hardness_rating + " " + short_data;
            tooltip_div.append($j("<div/>").addClass("tooltip_title").html(short_data));
            tooltip_div.append($j("<div/>").html(section.num_students_checked_in.toString() + " students checked in, " + section.num_students_enrolled + " enrolled; capacity = " + section.capacity));
            tooltip_div.append($j("<div/>").addClass("tooltip_teachers").html(class_data.teacher_names));
            tooltip_div.append($j("<div/>").attr("id", "tooltip_" + section.id + "_" + ts_id + "_desc").addClass("tooltip_description").html(class_data.class_info));
            if(class_data.prereqs)
            {
                tooltip_div.append($j("<div/>").attr("id", "tooltip_" + section.id + "_" + ts_id + "_prereq").addClass("tooltip_prereq").html("Prereqs: " + class_data.prereqs));
            }
            new_div.append(tooltip_div);
            
            //  Set color of the cell based on check-in and enrollment of the section
            var hue = 0.4 + 0.4 * (section.num_students_enrolled / section.capacity);
            if (section.num_students_enrolled >= section.capacity)
                hue = 1.0;
            var lightness = 0.9;
            if (settings.checkin_colors)
                lightness -= 0.5 * (section.num_students_checked_in / section.num_students_enrolled);
            var saturation = 0.8;
            if (hue > 1.0)
                hue = 1.0;
            if (section.num_students_enrolled == 0)
                lightness = 0.9;
            new_div.css("background", hslToHTML(hue, saturation, lightness));
            new_div.attr("id", "section_" + section.id + "_" + ts_id);

            classes_div.append(new_div);
        }

        


        ts_div.append(classes_div);
        ts_div.append($j("<div/>").addClass("timeslot_header").html(data.timeslots[ts_id].label));
    }
    update_category_filters(); // show/hide classes by category
}
    
function render_status_table()
{
    render_table("status", null);
    add_message("Displaying status matrix", "message_header");
    add_message("To view/change classes for a student, begin typing their name or ID number into the box below; then click on an entry, or use the arrow keys and Enter to select a student.");
}

/*  This function turns the data structure populated by handle_completed()
    
*/
function render_classchange_table(student_id)
{
    render_table("classchange", student_id);
    update_checkboxes();
    var studentLabel = data.students[student_id].first_name + " " + data.students[student_id].last_name + " (" + student_id + ")";
    add_message("Displaying class changes matrix for " + studentLabel + ", grade " + data.students[student_id].grade, "message_header");

}

/*  This function populates the linked data structures once all components have arrived.
*/

function update_category_filters()
{   
    $j(".section").removeClass("section_category_hidden");
    for (var id_str in data.categories)
    {
        var id = parseInt(id_str);

        if (!settings.categories_to_display[id])
        {
            console.log("Hiding category .section_category_" + id);
            $j(".section_category_" + id).not(".student_enrolled").addClass("section_category_hidden");
        }
    }
    if (!settings.categories_to_display[open_class_category.id])
    {
        console.log("Hiding walk-ins");
        $j(".section_category_" + open_class_category.id).not(".student_enrolled").addClass("section_category_hidden");
    }
}

function toggle_categories() {
    var showAll = $j(this).prop("id") == "category_show_all";

    for(var key in data.categories) {
        settings.categories_to_display[parseInt(key)] = showAll;
    }
    
    $j("#category_list :checkbox").not(".category_selector")
                                  .not("#category_select_" + open_class_category.id)
                                  .prop('checked', showAll);
    update_category_filters();

}

function extract_category_id(element_id) 
{
    return parseInt(element_id.split("_")[2]);
}

function render_category_options()
{
    //  Clear category select area
    top_div = $j("#category_list");
    top_div.html("");

    //  Add a checkbox for each category we know about
    function add_category_checkbox(category)
    {
        var id = category.id;
        var new_li = $j("<div/>").addClass("category_item");
        var new_checkbox = $j("<input/>").attr("type", "checkbox").attr("id", "category_select_" + id);

        if (settings.categories_to_display[id]) {
            new_checkbox.attr("checked", "checked");
        }

        new_checkbox.change(function (event) {
            var target_id = extract_category_id(event.target.id);
            settings.categories_to_display[target_id] = !settings.categories_to_display[target_id];
            update_category_filters();
        });

        new_li.append(new_checkbox);
        new_li.append($j("<span/>").html(category.symbol + ": " + category.category));
        top_div.append(new_li);
    }
    for (var key in data.categories) {
        var category = data.categories[key];
        add_category_checkbox(category);
    }
    add_category_checkbox(open_class_category);

    //initialize select all/none
    $j('.category_selector').click(toggle_categories);
}

function populate_classes()
{
    data.timeslots = {};
    data.classes = {};
    data.sections = {};
    data.categories = {}
    
    //  Fill in categories
    for (var i in data.catalog.categories)
    {
        var new_category = data.catalog.categories[i];

        data.categories[new_category.id] = new_category;
        if (settings.categories_to_display[new_category.id] === undefined)
        {
            settings.categories_to_display[new_category.id] = true;
        }
    }

    //  Fill in timeslots (we need these)
    for (var i in data.catalog.timeslots)
    {
        var new_ts = {};
        new_ts.id = data.catalog.timeslots[i][0];
        new_ts.label = data.catalog.timeslots[i][1];
        new_ts.startTimeMillis = data.catalog.timeslots[i][2];
        new_ts.sections = [];
        data.timeslots[new_ts.id] = new_ts;
    }
    
    //  Fill in classes
    for (var i in data.catalog.classes)
    {
        var new_cls = data.catalog.classes[i];
        new_cls.teachers = new_cls.teacher_names;
        data.classes[new_cls.id] = new_cls;
    }
    
    //  Fill in sections
    for (var i in data.catalog.sections)
    {
        var new_sec = data.catalog.sections[i];
        var parent_class = data.classes[new_sec.parent_class__id];
        
        //  Give up if we don't have a parent class for some strange reason...
        if (!parent_class)
            continue;
        
        new_sec.class_id = new_sec.parent_class__id;
        new_sec.emailcode = parent_class.category__symbol + new_sec.parent_class__id;
        new_sec.title = parent_class.title;
        new_sec.grade_min = parent_class.grade_min;
        new_sec.grade_max = parent_class.grade_max;
        new_sec.rooms = null;
        new_sec.students_enrolled = [];
        new_sec.students_checked_in = [];
        new_sec.num_students_enrolled = 0;
        new_sec.num_students_checked_in = 0;
        //  Place max capacity here, and lower it later if it turns out the room is smaller
        new_sec.capacity = parent_class.class_size_max;
        if ((parent_class.class_size_max == 0) || ((parent_class.class_size_max_optimal) && (parent_class.class_size_max_optimal < new_sec.capacity)))
            new_sec.capacity = parent_class.class_size_max_optimal;
        if ((new_sec.max_class_capacity) && (new_sec.max_class_capacity < new_sec.capacity))
            new_sec.capacity = new_sec.max_class_capacity;
        new_sec.timeslots = new_sec.event_ids.split(",");
        for (var j in new_sec.timeslots)
        {
            if (data.timeslots[parseInt(new_sec.timeslots[j])])
                data.timeslots[parseInt(new_sec.timeslots[j])].sections.push(new_sec.id);
        }
        
        data.sections[new_sec.id] = new_sec;
    }
    
    //  Sort sections within each timeslot
    for (var i in data.timeslots)
    {
        data.timeslots[i].sections.sort();
    }
}

function populate_students()
{
    data.students = {};
    
    //  Initialize students array
    for (var i in data.students_list)
    {
        var new_student = {};
        new_student.id = data.students_list[i][0];
        new_student.last_name = data.students_list[i][1];
        new_student.first_name = data.students_list[i][2];
        new_student.grade = 0;
        new_student.sections = [];
        new_student.checked_in = null;
        data.students[new_student.id] = new_student;
    }
    
    //  Initialize student selector autocomplete
    setup_autocomplete();
}

function populate_rooms()
{
    //  Assign rooms
    for (var i in data.rooms)
    {
        data.sections[data.rooms[i][0]].rooms = data.rooms[i][1];
    
        //  Lower capacity to that of room if needed
        if (data.rooms[i][2] < data.sections[data.rooms[i][0]].capacity)
            data.sections[data.rooms[i][0]].capacity = data.rooms[i][2];
            
        //  If section still doesn't have a capacity, mark it as 1000
        if (!(data.sections[data.rooms[i][0]].capacity))
            data.sections[data.rooms[i][0]].capacity = 2000;
    }
}

function populate_enrollments()
{
    //  Assign students
    for (var i in data.enrollments)
    {
        var user_id = data.enrollments[i][0];
        if (!(user_id in data.students))
        {
            //  console.log("Warning: student ID " + user_id + " was not found in initial list");
            var new_user = {};
            new_user.id = user_id
            new_user.sections = [];
            new_user.checked_in = false;
            data.students[user_id] = new_user;
        }
        if (data.enrollments[i][1] in data.sections)
        {
            data.sections[data.enrollments[i][1]].students_enrolled.push(user_id);
            data.sections[data.enrollments[i][1]].num_students_enrolled++;
            data.students[user_id].sections.push(data.enrollments[i][1]);
        }
        else
        {
            //  console.log("Section " + data.enrollments[i][1] + " from enrollments is not present in catalog");
        }
    }
}

function populate_checkins()
{
    //  Assign checkins
    for (var i in data.checkins)
    {
        var user_id = data.checkins[i];
        if (user_id in data.students)
        {
            data.students[user_id].checked_in = true;
            for (var j in data.students[user_id].sections)
            {
                data.sections[data.students[user_id].sections[j]].students_checked_in.push(user_id);
                data.sections[data.students[user_id].sections[j]].num_students_checked_in++;
            }
        }
        else
        {
            //  console.log("User " + user_id + " from checkins is not present");
        }
    }
}

function populate_counts()
{
    //  Assign student counts (consistency check)
    for (var i in data.counts)
    {
        var sec_id = data.counts[i][0];
        var num_students = data.counts[i][1];
        
        //  If we have a conflict, assume the larger number of students are enrolled.
        if (!data.sections[sec_id])
            console.log("Could not find section " + sec_id);
        else if (data.sections[sec_id].num_students_enrolled != num_students)
        {
            //  console.log("Warning: Section " + sec_id + " claims to have " + num_students + " students but " + data.sections[sec_id].num_students_enrolled + " are enrolled.");
            if (num_students > data.sections[sec_id].num_students_enrolled)
                data.sections[sec_id].num_students_enrolled = num_students;
        }
    }
}

function handle_completed()
{
    //  console.log("All data has been received.");
    populate_classes();
    populate_students();
    populate_rooms();
    populate_enrollments();
    populate_checkins();
    populate_counts();

    //  This line would set catalog_received, counts_received, etc. to false.
    //  At the very least it needs to be done immediately before refreshing the full table.
    //  reset_status();
    
    //  $j("#messages").html("");
    //  console.log("All data has been processed.");
    
    //  Re-draw the table of sections in the appropriate mode.
    if (state.display_mode == "status")
        set_current_student(null);
    else if (state.display_mode == "classchange")
        set_current_student(state.student_id);
}

function fetch_all(avoid_catalog)
{
    reset_status();
    if (!avoid_catalog)
    {
        $j.ajax({
            url: program_base_url + "catalog_status",
            success: handle_catalog
        });
    }
    else
    {
        data_status.catalog_received = true;
    }
    $j.ajax({
        url: program_base_url + "enrollment_status",
        success: handle_enrollment
    });
    $j.ajax({
        url: program_base_url + "checkin_status",
        success: handle_checkins
    });
    $j.ajax({
        url: program_base_url + "counts_status",
        success: handle_counts
    });
    $j.ajax({
        url: program_base_url + "rooms_status",
        success: handle_rooms
    });
    $j.ajax({
        url: program_base_url + "students_status",
        success: handle_students
    });
}

function refresh_counts() {
    add_message("Pinging server for updated information, please stand by...", "message_header");
    fetch_all(true);
}

$j(document).scroll(function(){
    $j("#student_selector_area").css("left", window.scrollX);
});

$j(document).ready(function () {
    //  Send out initial requests for data.
    //  Once they have all completed, the results will be parsed and the
    //  class changes grid will be displayed.

    $j("#messages").html("Loading class and student data...");
    
    setup_settings();
    fetch_all();
    
    //  Update enrollment counts and list of students once per minute.
    setInterval(refresh_counts, 300000);
});
