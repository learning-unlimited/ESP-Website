/*  
    Javascript code for the onsite check-in interface.
    
    This could easily be merged into a more general library for client-side admin views,
    since it fetches a lot of data from the server and builds data structures in the
    browser which are kind of like a simplified version of our server-side DB schema.
*/

//  This is the primary data structure for all received data.
var data = {};

/*  Ajax status flags
    We request multiple chunks of data from the server concurrently
    and have to wait for all of them to arrive before we populate the
    internal data structures.
*/

//  This is a set of flags for whether each batch of JSON data has arrived
var status = {
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
    status.catalog_received = false;
    status.enrollment_received = false;
    status.checkins_received = false;
    status.counts_received = false;
    status.rooms_received = false;
    status.students_received = false;
}

//  This function only returns true if all flags have been set
//  (i.e. we received all necessary data)
function check_status()
{
    if (!status.catalog_received)
        return false;
    if (!status.enrollment_received)
        return false;
    if (!status.checkins_received)
        return false;
    if (!status.counts_received)
        return false;
    if (!status.rooms_received)
        return false;
    if (!status.students_received)
        return false;
        
    return true;
}

//  This is a state variable.
var state = {
    status: status,
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
    status.catalog_received = true;
    if (check_status())
        handle_completed();
}

function handle_counts(new_data, text_status, jqxhr)
{
    data.counts = new_data;
    status.counts_received = true;
    if (check_status())
        handle_completed();
}

function handle_enrollment(new_data, text_status, jqxhr)
{
    data.enrollments = new_data;
    status.enrollment_received = true;
    if (check_status())
        handle_completed();
}

function handle_checkins(new_data, text_status, jqxhr)
{
    data.checkins = new_data;
    status.checkins_received = true;
    if (check_status())
        handle_completed();
}

function handle_rooms(new_data, text_status, jqxhr)
{
    data.rooms = new_data;
    status.rooms_received = true;
    if (check_status())
        handle_completed();
}

function handle_students(new_data, text_status, jqxhr)
{
    data.students_list = new_data;
    status.students_received = true;
    if (check_status())
        handle_completed();
}

/*  Event handlers  */

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
            if (section.num_students_enrolled >= section.capacity)
                studentcheckbox.attr("disabled", "disabled");
            else
                studentcheckbox.change(handle_checkbox);
        }
    }
    
    for (var i in state.student_schedule)
    {
        var section = data.sections[state.student_schedule[i]];
        for (var j in section.timeslots)
        {
            var studentcheckbox = $j("#classchange_" + section.id + "_" + state.student_id + "_" + section.timeslots[j]);
            $j("#section_" + section.id + "_" + section.timeslots[j]).addClass("student_enrolled");
            studentcheckbox.attr("checked", "checked");
            studentcheckbox.removeAttr("disabled");
            studentcheckbox.change(handle_checkbox);
        }
    }

    //  console.log("Refreshed checkboxes");
}

function handle_schedule_response(new_data, text_status, jqxhr)
{
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
            url: "/onsite/Splash/2010/get_schedule_json?user=" + student_id,
            async: false,
            success: handle_schedule_response
        });
        render_classchange_table(student_id);
        $j("#status_switch").removeAttr("disabled");
        $j("#status_switch").click(function () {set_current_student(null);});
    }
    else
    {
        state.student_id = null;
        state.display_mode = "status";
        render_status_table();
        $j("#student_selector").attr("value", "");
        $j("#status_switch").attr("disabled", "disabled");
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
    data.conflicts[event.target.id] = null;
}

//  Add a student to a class
function add_student(student_id, section_id)
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
        url: "/onsite/Splash/2010/update_schedule_json?user=" + student_id + "&sections=[" + new_sections.toString() + "]",
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
        url: "/onsite/Splash/2010/update_schedule_json?user=" + student_id + "&sections=[" + new_sections.toString() + "]",
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
    if (event.target.checked)
    {
        //  console.log("Handling CHECKING of " + event.target.id);
        add_student(target_info[2], target_info[1]);
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
    var s = ui.item.value;
    var student_id = s.slice(s.indexOf("(")+1, s.indexOf(")"));
    
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
    for (var i in data.students)
    {
        student_strings.push(data.students[i].first_name + " " + data.students[i].last_name + " (" + i + ")");
    }

    $j("#student_selector").autocomplete({
        source: student_strings,
        select: autocomplete_select_item
  	});
}

function clear_table()
{
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
function render_table(display_mode, student_id)
{
    clear_table();
    for (var ts_id in data.timeslots)
    {
        var div_name = "timeslot_" + ts_id;
        var ts_div = $j("#" + div_name);
        
        ts_div.append($j("<div/>").addClass("timeslot_header").html(data.timeslots[ts_id].label));
        for (var i in data.timeslots[ts_id].sections)
        {
            var section = data.sections[data.timeslots[ts_id].sections[i]];
            var new_div = $j("<div/>").addClass("section");
            
            if (display_mode == "classchange")
            {
                var studentcheckbox = $j("<input/>").attr("type", "checkbox").attr("id", "classchange_" + section.id + "_" + student_id + "_" + ts_id).addClass("classchange_checkbox");
                //  Parameters of these checkboxes will be set in the update_checkboxes() function above
                new_div.append(studentcheckbox);
            }
            
            if ((display_mode == "status") || ((section.grade_min <= data.students[student_id].grade) && (section.grade_max >= data.students[student_id].grade)))
            {
                new_div.append($j("<span/>").addClass("emailcode").html(section.emailcode));
                new_div.append($j("<span/>").addClass("room").html(section.rooms));
                //  TODO: make this snap to the right reliably
                new_div.append($j("<span/>").addClass("studentcounts").html(section.num_students_checked_in.toString() + "/" + section.num_students_enrolled + "/" + section.capacity));
                
                //  Create a tooltip with more information about the class
                tooltip_div = $j("<span/>").addClass("tooltip_hover");
                tooltip_div.append($j("<div/>").addClass("tooltip_title").html(section.title));
                var teacher_txt = "";
                for (var t in data.classes[section.class_id].teachers)
                {
                    teacher_txt += data.classes[section.class_id].teachers[t].first_name + " " + data.classes[section.class_id].teachers[t].last_name;
                    if (t < data.classes[section.class_id].teachers.length - 1)
                        teacher_txt += ", ";
                }
                tooltip_div.append($j("<div/>").addClass("tooltip_teachers").html(teacher_txt));
                tooltip_div.append($j("<div/>").addClass("tooltip_grades").html("Grades " + data.classes[section.class_id].grade_min.toString() + "--" + data.classes[section.class_id].grade_max.toString()));
                tooltip_div.append($j("<div/>").addClass("tooltip_description").html(data.classes[section.class_id].class_info));

                new_div.append(tooltip_div);
                
                //  Set color of the cell based on check-in and enrollment of the section
                var hue = 0.4 + 0.6 * (section.num_students_enrolled / section.capacity);
                var lightness = 0.9 - 0.5 * (section.num_students_checked_in / section.num_students_enrolled);
                var saturation = 0.8;
                if (hue > 1.0)
                    hue = 1.0;
                if (section.num_students_enrolled == 0)
                    lightness = 0.9;
                new_div.css("background", hslToHTML(hue, saturation, lightness));
                new_div.attr("id", "section_" + section.id + "_" + ts_id);
                
                //  Create tooltip with class description, teachers
                new_div.addClass("tooltip");
                var hover_div = $j("<span/>").addClass("tooltip").addClass("tooltip_hover");
                hover_div.html("Hi, this is a tooltip");
                hover_div.attr("id", "section_" + section.id + "_tooltip");
                //  TODO: FIX
                //  new_div.append(hover_div);
                
                ts_div.append(new_div);
            }
        }
    }
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
    add_message("Displaying class changes matrix for " + data.students[student_id].first_name + " " + data.students[student_id].last_name + " (" + student_id + "), grade " + data.students[student_id].grade, "message_header");
}

/*  This function populates the linked data structures once all components have arrived.
*/

function handle_completed()
{
    //  console.log("All data has been received.");
    
    data.students = {};
    data.classes = {};
    data.sections = {};
    data.timeslots = {};
    
    //  Iterate over classes/sections in the catalog
    for (var cls in data.catalog)
    {
        //  Copy class object to dictionary
        data.classes[data.catalog[cls].id] = data.catalog[cls];
    
        for (var sec in data.catalog[cls].get_sections)
        {
            //  Construct simplified section object
            var new_sec = {};
            new_sec.id = data.catalog[cls].get_sections[sec].id;
            new_sec.class_id = data.catalog[cls].id;
            new_sec.title = data.catalog[cls].title;
            new_sec.grade_min = data.catalog[cls].grade_min;
            new_sec.grade_max = data.catalog[cls].grade_max;
            new_sec.rooms = null;
            new_sec.emailcode = data.catalog[cls].category.symbol + data.catalog[cls].id + "s" + (parseInt(sec)+1);
            new_sec.students_enrolled = [];
            new_sec.students_checked_in = [];
            new_sec.num_students_enrolled = 0;
            new_sec.num_students_checked_in = 0;
            new_sec.capacity = data.catalog[cls].get_sections[sec].capacity;
            new_sec.timeslots = [];
            data.sections[new_sec.id] = new_sec;
            
            //  Create timeslot if it doesn't exist already
            var ts = data.catalog[cls].get_sections[sec].get_meeting_times;
            for (var i in ts)
            {
                if (!(ts[i].id in data.timeslots))
                {
                    var new_ts = {};
                    new_ts.id = ts[i].id;
                    
                    new_ts.label = ts[i].short_description;
                    new_ts.sections = [];
                    data.timeslots[new_ts.id] = new_ts;
                    //  console.log("Added timeslot ID " + new_ts.id + ": " + new_ts.label);
                }
                data.sections[new_sec.id].timeslots.push(ts[i].id);
                data.timeslots[ts[i].id].sections.push(new_sec.id);
                //  console.log("Added " + data.catalog[cls].title + " section ID " + data.catalog[cls].get_sections[sec].id + " to timeslot " + ts[i].id);
            }
        }
    }
    
    //  Sort sections within each timeslot
    for (var i in data.timeslots)
    {
        data.timeslots[i].sections.sort();
    }
    
    //  Initialize students array
    for (var i in data.students_list)
    {
        var new_student = {};
        new_student.id = data.students_list[i][0];
        new_student.last_name = data.students_list[i][1];
        new_student.first_name = data.students_list[i][2];
        new_student.grade = data.students_list[i][3];
        new_student.sections = [];
        new_student.checked_in = null;
        data.students[new_student.id] = new_student;
    }
    
    //  Assign rooms
    for (var i in data.rooms)
    {
        data.sections[data.rooms[i][0]].rooms = data.rooms[i][1];
    }
    
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
    
    //  Initialize student selector autocomplete
    setup_autocomplete();
    
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
    
    //  Assign student counts (consistency check)
    for (var i in data.counts)
    {
        var sec_id = data.counts[i][0];
        var num_students = data.counts[i][1];
        
        //  If we have a conflict, assume the larger number of students are enrolled.
        if (data.sections[sec_id].num_students_enrolled != num_students)
        {
            //  console.log("Warning: Section " + sec_id + " claims to have " + num_students + " students but " + data.sections[sec_id].num_students_enrolled + " are enrolled.");
            if (num_students > data.sections[sec_id].num_students_enrolled)
                data.sections[sec_id].num_students_enrolled = num_students;
        }
    }
    
    //  This line would set catalog_received, counts_received, etc. to false.
    //  At the very least it needs to be done immediately before refreshing the full table.
    //  reset_status();
    
    $j("#messages").html("");
    //  console.log("All data has been processed.");
    
    //  Re-draw the table of sections in the appropriate mode.
    if (state.display_mode == "status")
        set_current_student(null);
    else if (state.display_mode == "classchange")
        set_current_student(state.student_id);
}

$j(document).ready(function () {
    //  Send out initial requests for data.
    //  Once they have all completed, the results will be parsed and the
    //  class changes grid will be displayed.

    $j("#messages").html("Loading class and student data...");
    
    $j.ajax({
        url: "/learn/Splash/2010/catalog_json",
        success: handle_catalog
    });
    $j.ajax({
        url: "/onsite/Splash/2010/enrollment_status",
        success: handle_enrollment
    });
    $j.ajax({
        url: "/onsite/Splash/2010/checkin_status",
        success: handle_checkins
    });
    $j.ajax({
        url: "/onsite/Splash/2010/counts_status",
        success: handle_counts
    });
    $j.ajax({
        url: "/onsite/Splash/2010/rooms_status",
        success: handle_rooms
    });
    $j.ajax({
        url: "/onsite/Splash/2010/students_status",
        success: handle_students
    });
    
});
