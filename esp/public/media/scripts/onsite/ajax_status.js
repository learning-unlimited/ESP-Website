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
    show_class_titles: false,
    show_class_teachers: false,
    show_class_rooms: false,
    show_closed_reg: false,
    hide_past_time_blocks: false,
    hide_conflicting: false,
    search_term: "",
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
    full_received: false,
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
    data_status.full_received = false;
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
    if (!data_status.full_received)
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

function handle_full(new_data, text_status, jqxhr)
{
    data.full = new_data;
    data_status.full_received = true;
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

function handle_settings_change(event)
{
    setup_settings();
    render_table(state.display_mode, state.student_id);
}

function setup_settings()
{
    $j("#hide_full_control").unbind("change");
    $j("#override_control").unbind("change");
    $j("#grade_limits_control").unbind("change");
    $j("#show_class_titles").unbind("change");
    $j("#show_class_teachers").unbind("change");
    $j("#show_class_rooms").unbind("change");
    $j("#show_closed_reg").unbind("change");
    $j("#hide_past_time_blocks").unbind("change");
    $j("#hide_conflicting").unbind("change");


    //  Apply settings
    settings.show_full_classes = $j("#hide_full_control").prop("checked");
    settings.override_full = $j("#override_control").prop("checked");
    settings.disable_grade_filter = $j("#grade_limits_control").prop("checked");
    settings.show_class_titles = $j("#show_class_titles").prop("checked");
    settings.show_class_teachers = $j("#show_class_teachers").prop("checked");
    settings.show_class_rooms = $j("#show_class_rooms").prop("checked");
    settings.show_closed_reg = $j("#show_closed_reg").prop("checked");
    settings.hide_past_time_blocks = $j("#hide_past_time_blocks").prop("checked");
    settings.hide_conflicting = $j("#hide_conflicting").prop("checked");

    $j("#hide_full_control").change(handle_settings_change);
    $j("#override_control").change(handle_settings_change);
    $j("#grade_limits_control").change(handle_settings_change);
    $j("#show_class_titles").change(handle_settings_change);
    $j("#show_class_teachers").change(handle_settings_change);
    $j("#show_class_rooms").change(handle_settings_change);
    $j("#show_closed_reg").change(handle_settings_change);
    $j("#hide_past_time_blocks").change(handle_settings_change);
    $j("#hide_conflicting").change(handle_settings_change);
}

function hide_sidebar()
{
    $j("#side_area").addClass("sidebar_hidden");
    $j("#main_area").addClass("sidebar_hidden");
}

function show_sidebar()
{
    $j("#side_area").removeClass("sidebar_hidden");
    $j("#main_area").removeClass("sidebar_hidden");
}

function setup_sidebar()
{
    $j("#hide_sidebar").click(hide_sidebar);
    $j("#show_sidebar").click(show_sidebar);
}

function update_search_filter()
{
    // unhide all classes first
    $j(".section").removeClass("section_search_hidden");
    for (var section_id in data.sections)
    {
        var section = data.sections[section_id];

        // check if the class matches the search
        if (section.emailcode.toLowerCase().indexOf(settings.search_term.toLowerCase()) != -1 ||
            section.title.toLowerCase().indexOf(settings.search_term.toLowerCase()) != -1 ||
            data.classes[section.class_id].teacher_names.toLowerCase().indexOf(settings.search_term.toLowerCase()) != -1)
            continue;

        // no match; hide the class
        for (var j in section.timeslots)
        {
            var section_elem = $j("#section_" + section.id + "_" + section.timeslots[j]);
            section_elem.addClass("section_search_hidden");
        }
    }
    // unhide enrolled classes
    $j(".student_enrolled").removeClass("section_search_hidden");
}

function handle_search(event)
{
    settings.search_term = $j("#class_search").val();
    update_search_filter();
}

function setup_search()
{
    settings.search_term = $j("#class_search").val();
    $j("#class_search").keyup(handle_search);
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
        dataType: 'json',
        success: function (data, text_status, jqxhr) {
            add_message(data.message);
        }
    });
}

function add_message(msg, cls)
{
    if (!cls)
        $j("#messages").append($j("<div/>").addClass("message").html(msg));
    else
        $j("#messages").append($j("<div/>").addClass(cls).html(msg));
    $j("#messages").prop("scrollTop", $j("#messages").prop("scrollHeight"));
}

function disable_checkboxes()
{
    $j(".classchange_checkbox").attr("disabled", "disabled");
    $j(".classchange_checkbox").unbind("change");
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
            if ((section.full) && (!(settings.override_full)))
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
    
    function return_section(sched_td) {
        // Move entire old section back to original row
        if (sched_td.data("section") != undefined & sched_td.data("row") != undefined){
            var sec_id = sched_td.data("section");
            var sec_row = sched_td.data("row");
            for (var ts_id of data.sections[sec_id].event_ids) {
                var sched_td_old = $j(".schedule > .timeslot_" + ts_id);
                var section_td_blank = $j(".sections").eq(sec_row).children(".timeslot_" + ts_id);
                // Move old section into original row
                section_td_blank.replaceWith(sched_td_old.clone(true));
                // Clear spot in schedule
                sched_td_old.replaceWith($j("<td/>").addClass("timeslot_" + ts_id));
            }
        }
    }

    // Find the classes that the student is enrolled in,
    // highlight them and bring them to the top.
    var occupied_timeslots = {};
    for (var i in state.student_schedule)
    {
        var section = data.sections[state.student_schedule[i]];
        for (var j in section.timeslots)
        {
            // Get current section in schedule
            var sched_td = $j(".schedule > .timeslot_" + section.timeslots[j]);
            if (sched_td.hasClass("section")){
                return_section(sched_td);
            }
            occupied_timeslots[section.timeslots[j]] = section.id;
            var section_td = $j("#section_" + section.id + "_" + section.timeslots[j]);
            var section_td_old = section_td.clone(true);
            // Replace section td with blank td
            section_td.replaceWith($j("<td/>").addClass("timeslot_" + section.timeslots[j]));
            section_td_old.addClass("student_enrolled");
            // Move section into schedule
            sched_td = $j(".schedule > .timeslot_" + section.timeslots[j]);
            sched_td.replaceWith(section_td_old);
            var studentcheckbox = $j("#classchange_" + section.id + "_" + state.student_id + "_" + section.timeslots[j]);
            studentcheckbox.attr("checked", "checked");
            studentcheckbox.removeAttr("disabled");
            studentcheckbox.unbind("change");
            studentcheckbox.change(handle_checkbox);
        }
    }
    
    // Move other sections back into grid
    $j(".schedule > .section:not(.student_enrolled)").each(function() {
        return_section($j(this));
    });

    if (settings.hide_conflicting)
    {
        // For each timeslot where the student is enrolled in a class,
        // hide the other classes that overlap with that timeslot.
        $j(".section").removeClass("section_conflict_hidden");
        for (var ts_id in occupied_timeslots)
        {
            for (var i in data.timeslots[ts_id].sections)
            {
                var section = data.sections[data.timeslots[ts_id].sections[i]];
                if (occupied_timeslots[ts_id] == section.id)
                    continue;

                for (var j in section.timeslots)
                {
                    var section_elem = $j("#section_" + section.id + "_" + section.timeslots[j]);
                    section_elem.addClass("section_conflict_hidden");
                }
            }
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
            dataType: 'json',
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

function check_conflicts(event)
{
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

function lock_schedule() {
    if (state.schedule_locked) {
        // Couldn't acquire the lock.
        return false;
    }
    state.schedule_locked = true;
    return true;
}

function unlock_schedule() {
    state.schedule_locked = false;
}

//  Add a student to a class
function add_student(student_id, section_id, size_override)
{
    if (!lock_schedule()) {
        console.log("Warning: schedule locked, refusing to add section " + section_id);
        return;
    }
    disable_checkboxes();

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
        dataType: 'json',
        success: handle_schedule_response,
        complete: [update_checkboxes, unlock_schedule]
    });
}

//  Remove a student from a class
function remove_student(student_id, section_id)
{
    if (!lock_schedule()) {
        console.log("Warning: schedule locked, refusing to remove section " + section_id);
        return;
    }
    disable_checkboxes();

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
        dataType: 'json',
        success: handle_schedule_response,
        complete: [update_checkboxes, unlock_schedule]
    });
}

function register_student(student_id, dialog) 
{
    // Add a dummy entry to data.students for now, in case anything
    // tries to access it.
    // The real data will be populated by the call to fetch_all() below.
    var new_student = {};
    new_student.id = student_id;
    new_student.first_name = "Unknown";
    new_student.last_name = "Student";
    new_student.grade = 0;
    new_student.sections = [];
    new_student.checked_in = null;
    data.students[student_id] = new_student;
   
    $j.ajax({
            url: program_base_url + "register_student",
            type:'POST',
            data: {
                csrfmiddlewaretoken: csrf_token(),
                student_id: student_id
            },

            success: function(data) {
                if(data.status) {
                    fetch_all();
                    set_current_student(parseInt(student_id));
                    dialog.dialog("close");
                } else {
                    $j('#not-registered-msg').hide();
                    $j('#noinfo-msg').show();
                    $j("#dialog-confirm-button-register").button("disable");
                }
            },

            error: function (result) {
                console.log(result);
            }
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
            if (target_section.full)
            {
                verified = confirm("This class is full or oversubscribed, with " + target_section.num_students_enrolled + " students enrolled and " + target_section.capacity + " spots. Of the enrolled students, " + target_section.num_students_checked_in + " are checked in to the program and " + target_section.num_students_attending + " have been marked as attending this class. Are you sure you want to register the additional student?");
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

function autocomplete_select_item(event, ui)
{
    event.preventDefault();
    
    last_select_event = [event, ui];
    var student_id = ui.item.value;
    //  Refresh the table of checkboxes for the newly selected student.

    if ((student_id > 0) && (student_id < 99999999)) 
    {
        if(ui.item.noProfile)
        {
            var dialog = $j("#dialog-confirm");
            $j("#not-registered-msg").show();
            $j("#noinfo-msg").hide();
            $j("#dialog-confirm-button-register").button("enable");
            dialog.data('student_id', student_id);
            dialog.dialog('open');
        }
        else 
        {
            fetch_all();
            set_current_student(parseInt(student_id));
        }
        
    }    
    else
    {
        console.log("Invalid student selected: " + student_id);
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
        studentItem.noProfile = false;

        student_strings.push(studentItem);
    }
    student_strings.sort(function (a, b) {
        if (a.label > b.label) {
            return 1;
        }
        if (a.label < b.label) {
            return -1;
        }
        return 0;
    });

    $j("#student_selector").autocomplete({
        width: 400,
        max: 20,
        source: function( request, response ) {
            var results = $j.ui.autocomplete.filter(student_strings, request.term);
            if (results.length >= 1) {
                response(results);
            }
            else {
                // expand search to entire student base
                $j.ajax({
                    url: program_base_url + "students_status",
                    data: {
                        q: request.term
                    },
                    success: function (new_data) {
                        var results = [];
                        for (var i in new_data) {
                            var student = new_data[i];
                            var id = student[0];
                            var last_name = student[1];
                            var first_name = student[2];
                            var has_profile = student[3];
                            var studentItem = {};
                            studentItem.value = id;
                            studentItem.label = first_name + " " + last_name + " (" + id + ")";
                            studentItem.noProfile = !has_profile;

                            results.push(studentItem);
                        }
                        response(results);

                    },
                    error: function (result) {
                        alert(result);
                        response(results);
                    }
                });
            }
        },
        select: autocomplete_select_item,
        focus: function( event, ui ) {
            $j( "#student_selector" ).val( ui.item.label );
            return false;
        },
    }).data("autocomplete")._renderItem = function (ul, item) {
        var listItem = $j("<li>")
                        .attr( "data-value", item.value )
                        .append("<a href='#'>" + item.label + "</a>")
                        .data("item.autocomplete", item);

        if(item.noProfile) {
            listItem.addClass('no-profile');
        }

        listItem.appendTo(ul);
        ul.css('z-index','30');
        return listItem
    }
}

function clear_table()
{
    $j("tr.sections, tr.schedule").remove();
    $j(".timeslot_header, .timeslot_footer").remove();
}



/*  This function turns the data structure populated by handle_completed() (below)
    into a table displaying the enrollment and check-in status of all sections. 
    Additional features are controlled by display_mode and student_id.  */
function render_table(display_mode, student_id)
{
    render_category_options();
    clear_table();
    if (display_mode == "classchange") {
        $j("<tr/>").addClass("schedule").insertAfter($j(".timeslot_headers"));
        var schedule = $j(".schedule");
    }
    var headers = $j(".timeslot_headers");
    var footers = $j(".timeslot_footers");
    var timeslots_ordered = Object.keys(data.timeslots)
    timeslots_ordered.sort((a, b) => (data.timeslots[a].startTimeMillis > data.timeslots[b].startTimeMillis) ? 1 : -1)
    //exclude timeslots that have a start time 20 minutes prior to the current time (if we're not showing past timeslots)
    if (settings.hide_past_time_blocks) {
        timeslots_ordered = timeslots_ordered.filter(ts_id => (Math.floor((Date.now() - data.timeslots[ts_id].startTimeMillis)/60000)) < minMinutesToHideTimeSlot);
    }
    for (var ts_id of timeslots_ordered)
    {
        var timeSlotHeader = data.timeslots[ts_id].label;

        headers.append($j("<th/>").addClass("timeslot_" + ts_id + " timeslot_header timeslot_top").html(timeSlotHeader));
        footers.append($j("<th/>").addClass("timeslot_" + ts_id + " timeslot_header").html(timeSlotHeader));
	
        if (display_mode == "classchange") {
            schedule.append($j("<td/>").addClass("timeslot_" + ts_id));
        }
    }
    
    //filter sections based on settings
    var filtered_sections = data.sections_sorted;
    if ((display_mode == "classchange") && (!(settings.disable_grade_filter))) {
        //if doing class changes (and we are filtering by grade)
        //exclude classes that are outside the student's grade and the student isn't already enrolled in
        filtered_sections = filtered_sections.filter(sec_id => !((state.student_schedule.indexOf(parseInt(sec_id)) == -1) &&
                                                               ((data.sections[sec_id].grade_min > data.students[student_id].grade) || (data.sections[sec_id].grade_max < data.students[student_id].grade))));
    }
    
    if (!(settings.show_full_classes)) {
        //if we are filtering full classes, exclude classes that are full and that the student isn't already enrolled in
        filtered_sections = filtered_sections.filter(sec_id => !((data.sections[sec_id].full) &&
                                                               ((display_mode == "status") || (state.student_schedule.indexOf(parseInt(sec_id)) == -1))));
    }
    
    if (!(settings.show_closed_reg)) {
        //exclude classes with closed registration and that the student isn't already enrolled in (if we're not showing closed classes)
        filtered_sections = filtered_sections.filter(sec_id => !((data.sections[sec_id].registration_status != 0) &&
                                                               ((display_mode == "status") || (state.student_schedule.indexOf(parseInt(sec_id)) == -1))));
    }
    
    //exclude classes in hidden categories (but not that the student is enrolled in)
    filtered_sections = filtered_sections.filter(sec_id => ((settings.categories_to_display[data.classes[data.sections[sec_id].class_id].category__id]) ||
                                                           ((display_mode == "classchange") && (state.student_schedule.indexOf(parseInt(sec_id)) != -1))));

    function check_timeslots(sec_id) {
        var section = data.sections[sec_id];
        for (var j in section.timeslots)
        {
            var sec_ts_id = section.timeslots[j];
            var startTimeMillis = data.timeslots[sec_ts_id].startTimeMillis;
            //excludes timeslots that have a start time 20 minutes prior to the current time
            var differenceInMinutes = Math.floor((Date.now() - startTimeMillis)/60000);

            if (differenceInMinutes > minMinutesToHideTimeSlot)
                return false;
        }
        return true;
    }
        
    //exclude the class if it started in the past (and we're not showing past timeblocks)
    if (settings.hide_past_time_blocks) {
        filtered_sections = filtered_sections.filter(sec_id => check_timeslots(sec_id));
    }
    
    for (var sec_id of filtered_sections)
    {
        var row = 0;
        var new_row = false;
        var section = data.sections[sec_id];
        var parent_class = data.classes[section.class_id];
        
        //find row closest to the top that can contain the event
        Loop1: while (true) {
            if (row >= $j("table#timeslots > * > tr.sections").length) {
                //we've run out of existing rows, need to make a new row
                new_row = true;
                break Loop1;
            }
            Loop2: for (var ts_id of section.event_ids) {
                var ts_tds = document.querySelectorAll('tr.sections .timeslot_'+ ts_id);
                if ($j(ts_tds[row]).hasClass('section')) {
                    //conflict in this row, check next row
                    row += 1;
                    break Loop2;
                }
                if (ts_id == section.event_ids[section.event_ids.length - 1]) {
                    //no conflicts in this row, use it
                    break Loop1;
                }
            }
        }
        
        //Make a custom td for the section in the specified timeslot
        function custom_td(ts_id) {
            var new_td = $j("<td/>").addClass("section");
            new_td.addClass("timeslot_" + ts_id);
            new_td.addClass("section_category_" + parent_class.category__id);
            new_td.data("section", section.id);
            new_td.data("row", row);
            
            if (display_mode == "classchange")
            {
                var studentcheckbox = $j("<input/>").attr("type", "checkbox").attr("id", "classchange_" + section.id + "_" + student_id + "_" + ts_id).addClass("classchange_checkbox");
                //  Parameters of these checkboxes will be set in the update_checkboxes() function above
                new_td.append(studentcheckbox);
            }
            
            new_td.append($j("<span/>").addClass("emailcode").html(section.emailcode));
            if (settings.show_class_rooms)
            {
                new_td.append($j("<span/>").addClass("room").html(section.rooms));
            }
            //  TODO: make this snap to the right reliably
            new_td.append($j("<span/>").addClass("studentcounts").attr("id", "studentcounts_" + section.id).html(section.num_students_attending.toString() + "/" + section.num_students_checked_in + "/" + section.num_students_enrolled + "/" + section.capacity));

            // Show the class title if we're not in compact mode
            if (settings.show_class_titles)
            {
                new_td.append($j("<div/>").addClass("title").html(section.title));
            }
            
            var class_data = data.classes[section.class_id];
            if (settings.show_class_teachers)
            {
                new_td.append($j("<div/>").addClass("teacher").html(class_data.teacher_names));
            }
            
            //  Create a tooltip with more information about the class
            new_td.addClass("tooltip");
            var tooltip_div = $j("<span/>").addClass("tooltip_hover");
            var short_data = section.title + " - Grades " + class_data.grade_min.toString() + "--" + class_data.grade_max.toString();
            if(class_data.hardness_rating) short_data = class_data.hardness_rating + " " + short_data;
            tooltip_div.append($j("<div/>").addClass("tooltip_title").html(short_data));
            // TODO: more reliable way to compute friendly_times?
            var first_timeslot = section.timeslots[0];
            var last_timeslot = section.timeslots[section.timeslots.length-1];
            var start_time = data.timeslots[first_timeslot].label.split("--")[0];
            var end_time = data.timeslots[last_timeslot].label.split("--")[1];
            var friendly_times = start_time + "--" + end_time + " (" + section.timeslots.length + " blocks)";
            tooltip_div.append($j("<div/>").html(friendly_times));
            tooltip_div.append($j("<div/>").html(section.num_students_attending.toString() + " students attending class, " + section.num_students_checked_in + " students checked in to program, " + section.num_students_enrolled + " enrolled; capacity = " + section.capacity));
            tooltip_div.append($j("<div/>").addClass("tooltip_teachers").html(class_data.teacher_names));
            tooltip_div.append($j("<div/>").attr("id", "tooltip_" + section.id + "_" + ts_id + "_desc").addClass("tooltip_description").html(class_data.class_info));
            if(class_data.prereqs)
            {
                tooltip_div.append($j("<div/>").attr("id", "tooltip_" + section.id + "_" + ts_id + "_prereq").addClass("tooltip_prereq").html("Prereqs: " + class_data.prereqs));
            }
            new_td.append(tooltip_div);
            
            //  Set color of the cell based on check-in and enrollment of the section
            var hue = 0.4 + 0.4 * (section.num_students_enrolled / section.capacity);
            if (section.full)
                hue = 1.0;
            var lightness = 0.9;
            if (settings.checkin_colors)
                lightness -= 0.5 * (section.num_students_checked_in / section.num_students_enrolled);
            var saturation = 0.8;
            if (hue > 1.0)
                hue = 1.0;
            if (section.num_students_enrolled == 0)
                lightness = 0.9;
            new_td.css("background", hslToHTML(hue, saturation, lightness));
            new_td.attr("id", "section_" + section.id + "_" + ts_id);
            
            //Style the td based on its position within all event_ids
            if (section.event_ids.length > 1) {
                var ts_ind = section.event_ids.indexOf(parseInt(ts_id));
                if (ts_ind > 0) {
                    new_td.addClass("section_left_open");
                }
                if (ts_ind < (section.event_ids.length - 1)){
                    new_td.addClass("section_right_open");
                }
            }
            return new_td;
        }
        
        if (new_row) {
            //make new row
            var new_tr = $j("<tr/>").addClass("sections").insertBefore($j(".timeslot_footers"));
            //loop through timeslots
            for (var ts_id of timeslots_ordered) {
                if (section.event_ids.includes(parseInt(ts_id))) {                    
                    //make section tds if timeslot in event_ids
                    var new_td = custom_td(ts_id);
                } else {
                    //blank tds otherwise
                    var new_td = $j("<td/>").addClass("timeslot_" + ts_id);
                }
                new_tr.append(new_td);
            }
        } else {
            //find existing blank cells and replace them
            for (var ts_id of section.event_ids) {
                var new_td = custom_td(ts_id);
                //Customize cell with other attributes
                var ts_tds = document.querySelectorAll('tr.sections .timeslot_'+ ts_id);
                $j(ts_tds[row]).replaceWith(new_td);
                
            }
        }
    }
    if (display_mode == "classchange") {
        update_checkboxes();
    }
    update_search_filter();
}
    
function render_status_table()
{
    render_table("status", null);
    add_message("Displaying status matrix", "message_header");
    add_message("To view/change classes for a student, begin typing their name or ID number into the box below; then click on an entry, or use the arrow keys and Enter to select a student.");
}

function render_classchange_table(student_id)
{
    render_table("classchange", student_id);
    var studentLabel = data.students[student_id].first_name + " " + data.students[student_id].last_name + " (" + student_id + ")";
    add_message("Displaying class changes matrix for " + studentLabel + ", grade " + data.students[student_id].grade, "message_header");

}

function toggle_categories() {
    var showAll = $j(this).prop("id") == "category_show_all";

    for(var key in data.categories) {
        settings.categories_to_display[parseInt(key)] = showAll;
    }
    
    $j("#category_list :checkbox").not(".category_selector")
                                  .not("#category_select_" + open_class_category.id)
                                  .prop('checked', showAll);
    render_table(state.display_mode, state.student_id);

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
            render_table(state.display_mode, state.student_id);
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

/*  This function populates the linked data structures once all components have arrived.
*/

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
        // Sort event_ids by start time of timeslots
        new_sec.event_ids.sort((a, b) => (data.timeslots[a].startTimeMillis > data.timeslots[b].startTimeMillis) ? 1 : -1)
        new_sec.timeslots = new_sec.event_ids;
        for (var j in new_sec.timeslots)
        {
            if (data.timeslots[parseInt(new_sec.timeslots[j])])
                data.timeslots[parseInt(new_sec.timeslots[j])].sections.push(new_sec.id);
        }
        
        data.sections[new_sec.id] = new_sec;
    }
    
    //do both of these now to speed up render_table()
    //filter out classes with no event_ids
    data.sections_sorted = Object.keys(data.sections).filter(sec_id => data.sections[sec_id].event_ids.length > 0)
    //sort sections by length (we want to plot the longer ones first, then fill in the gaps with the short ones)
    data.sections_sorted.sort((a, b) => (data.sections[a].event_ids.length < data.sections[b].event_ids.length) ? 1 : -1);
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
        var num_students_attending = data.counts[i][2];

        //  If we have a conflict, assume the larger number of students are enrolled.
        if (!data.sections[sec_id])
            console.log("Could not find section " + sec_id);
        else {
            data.sections[sec_id].num_students_attending = num_students_attending;
            if (data.sections[sec_id].num_students_enrolled != num_students)
            {
                //  console.log("Warning: Section " + sec_id + " claims to have " + num_students + " students but " + data.sections[sec_id].num_students_enrolled + " are enrolled.");
                if (num_students > data.sections[sec_id].num_students_enrolled)
                    data.sections[sec_id].num_students_enrolled = num_students;
            }
        }
    }
}

function populate_full()
{
    //  Assign full statuses
    for (var i in data.full)
    {
        var sec_id = data.full[i][0];
        var full = data.full[i][1];

        if (!data.sections[sec_id])
            console.log("Could not find section " + sec_id);
        else {
            if (full)
            {
                data.sections[sec_id].full = true;
            }
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
    populate_full();

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
            dataType: 'json',
            success: handle_catalog
        });
    }
    else
    {
        data_status.catalog_received = true;
    }
    $j.ajax({
        url: program_base_url + "enrollment_status",
        dataType: 'json',
        success: handle_enrollment
    });
    $j.ajax({
        url: program_base_url + "checkin_status",
        dataType: 'json',
        success: handle_checkins
    });
    $j.ajax({
        url: program_base_url + "counts_status",
        dataType: 'json',
        success: handle_counts
    });
    $j.ajax({
        url: program_base_url + "full_status",
        dataType: 'json',
        success: handle_full
    });
    $j.ajax({
        url: program_base_url + "rooms_status",
        dataType: 'json',
        success: handle_rooms
    });
    $j.ajax({
        url: program_base_url + "students_status",
        dataType: 'json',
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

$j(document).scroll(function () {
    // make timeslots stick to the top
    $j(".timeslot_top").each(function () {
        var scroll_top = window.scrollY;
        var top = $j(this).offset().top;
        var original_top = $j(this).data("original_top");
        if (original_top === undefined) {
            // non-sticky state
            if (scroll_top > top) {
                // change to sticky state
                $j(this).data("original_top", top);
                $j(this).offset({top: scroll_top});
                $j(this).css({'z-index': 10});
            }
        }
        else {
            // sticky state
            if (scroll_top < original_top) {
                // change to non-sticky state
                $j(this).removeData("original_top");
                $j(this).offset({top: original_top});
                $j(this).css({'z-index': 'auto'});
            }
            else {
                // stay in sticky state
                $j(this).offset({top: scroll_top});
            }
        }
    });
});

$j(document).ready(function () {
    //  Send out initial requests for data.
    //  Once they have all completed, the results will be parsed and the
    //  class changes grid will be displayed.

    var dialog = $j("#dialog-confirm").dialog({
        resizable: true,
        width: 450,
        height:250,
        modal: true,
        buttons: [{
            id: "dialog-confirm-button-register",
            text: "Register Account",
            click: function() {
                register_student($j(this).data('student_id'),$j(this));
            }
        },
        {
            id: "dialog-confirm-button-cancel",
            text: "Cancel",
            click: function() {
                $j(this).dialog( "close" );
            }
        }]
    });

    dialog.dialog("close");

    $j("#messages").html("Loading class and student data...");
    
    setup_settings();
    setup_sidebar();
    setup_search();
    fetch_all();
    
    //  Update enrollment counts and list of students once per minute.
    setInterval(refresh_counts, 300000);
});
