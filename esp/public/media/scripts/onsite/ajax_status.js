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

function update_checkboxes()
{
    $j(".student_enrolled").removeClass("student_enrolled");
    $j(".classchange_checkbox").removeAttr("checked");
    
    for (var i in state.student_schedule)
    {
        var section = data.sections[state.student_schedule[i]];
        for (var j in section.timeslots)
        {
            $j("#section_" + section.id + "_" + section.timeslots[j]).addClass("student_enrolled");
            $j("#classchange_" + section.id + "_" + state.student_id + "_" + section.timeslots[j]).attr("checked", "checked");
        }
    }
    //  console.log("Refreshed checkboxes");
}

function handle_schedule_response(new_data, text_status, jqxhr)
{
    //  Save the new schedule
    state.student_schedule = new_data.sections;
    state.student_schedule.sort();
    console.log("Updated schedule for student " + new_data.user);
    for (var i in new_data.messages)
    {
        var new_msg = $j("<div/>").addClass("message");
        new_msg.html(new_data.messages[i]);
        $j("#messages").append(new_msg);
    }
    
    //  Update the table if possible
    if (check_status())
        update_checkboxes();
}

//  Set the currently active student
function set_current_student(student_id)
{
    state.student_id = student_id;
    var schedule_resp = $j.ajax({
        url: "/onsite/Splash/2010/get_schedule_json?user=" + student_id,
        async: false,
        success: handle_schedule_response
    });
    render_classchange_table(student_id);
}

//  Add a student to a class
function add_student(student_id, section_id)
{
    if (state.student_id != student_id)
        console.log("Warning: student " + student_id + " is not currently selected for updates.");
        
    var new_sections = state.student_schedule;
    section_id = parseInt(section_id);
    
    //  TODO: Remove any conflicting classes
    
    console.log("add_student: Updated sections are " + new_sections.toString());
    
    //  Add desired section to list if it isn't already there
    if (new_sections.indexOf(section_id) == -1)
        new_sections.push(section_id);
    else
        console.log("Section " + section_id + " already found in current schedule");
    
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
        console.log("Warning: student " + student_id + " is not currently selected for updates.");
        
    var new_sections = state.student_schedule;
    section_id = parseInt(section_id);
    
    //  Remove desired section from list if it's there
    if (new_sections.indexOf(section_id) != -1)
        new_sections = new_sections.slice(0, new_sections.indexOf(section_id)).concat(new_sections.slice(new_sections.indexOf(section_id) + 1));
    else
        console.log("Section " + section_id + " not found in current schedule");
 
    console.log("remove_student: Updated sections are " + new_sections.toString());
   
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
        console.log("Invalid student selected: " + s);
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
                studentcheckbox.change(handle_checkbox)
                new_div.append(studentcheckbox);
            }
            
            if ((display_mode != "classchange") || ((section.grade_min <= data.students[student_id].grade) && (section.grade_max >= data.students[student_id].grade)))
            {
                new_div.append($j("<span/>").addClass("emailcode").html(section.emailcode));
                new_div.append($j("<span/>").addClass("room").html(section.rooms));
                //  TODO: make this snap to the right reliably
                new_div.append($j("<span/>").addClass("studentcounts").html(section.num_students_checked_in.toString() + "/" + section.num_students_enrolled + "/" + section.capacity));
                
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
    $j("#messages").html("Displaying status matrix");
}

/*  This function turns the data structure populated by handle_completed()
    
*/
function render_classchange_table(student_id)
{
    render_table("classchange", student_id);
    update_checkboxes();
    $j("#messages").html("Displaying class changes matrix for " + data.students[student_id].first_name + " " + data.students[student_id].last_name + " (" + student_id + ")");
}

/*  This function populates the linked data structures once all components have arrived.
*/

function handle_completed()
{
    console.log("All data has been received.");
    
    data.students = {};
    data.sections = {};
    data.timeslots = {};
    
    //  Iterate over classes/sections in the catalog
    for (var cls in data.catalog)
    {
        for (var sec in data.catalog[cls].get_sections)
        {
            //  Construct simplified section object
            var new_sec = {};
            new_sec.id = data.catalog[cls].get_sections[sec].id;
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
            console.log("Warning: student ID " + user_id + " was not found in initial list");
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
            console.log("Section " + data.enrollments[i][1] + " from enrollments is not present in catalog");
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
            console.log("User " + user_id + " from checkins is not present");
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
            console.log("Warning: Section " + sec_id + " claims to have " + num_students + " students but " + data.sections[sec_id].num_students_enrolled + " are enrolled.");
            if (num_students > data.sections[sec_id].num_students_enrolled)
                data.sections[sec_id].num_students_enrolled = num_students;
        }
    }
    
    //  This line would set catalog_received, counts_received, etc. to false.
    //  At the very least it needs to be done immediately before refreshing the full table.
    //  reset_status();
    
    $j("#messages").html("");
    console.log("All data has been processed.");
    
    //  Re-draw the table of sections in the appropriate mode.
    if (state.display_mode == "status")
        render_status_table();
    else if (state.display_mode == "classchange")
        render_classchange_table(state.student_id);
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
