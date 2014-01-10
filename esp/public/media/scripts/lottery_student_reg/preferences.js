// Functions to generate ids for HTML
function prefs_ts_div_from_id(id)
{
    return "pref_TS_"+id;
}
function prefs_ts_div_by_priority(id, priority)
{
    return prefs_ts_div_from_id(id) + (priority ? "_p" : "_i");
} 

// Appends an individual class section to the containerDiv
function render_class_section(data, container_div, class_section)
{
    container_div.append(data.sections[class_section].emailcode + ": " + data.sections[class_section].title + "<br/>");
}

// Appends the slot of priority preferences followed by the interested
// preferences for a given timeslot
function update_timeslot_prefs(data, container_div, timeslot_index)
{
    var timeslot_id = data.timeslots[timeslot_index].id;

    // Check to see if the timeslot div doesn't exist,
    // and set timeslot_div at the same time
    if ((timeslot_div = $j("#"+prefs_ts_div_from_id(timeslot_id))).length == 0)
    {
	// Create the div
	timeslot_div = $j("<div id='" + prefs_ts_div_from_id(timeslot_id) + "'></div>");
	container_div.append(timeslot_div);
	// Create the title
	timeslot_div.append("<h3>" + data.timeslots[timeslot_index].label + "</h3><br/>");
    }

    // Check if the interested div doesn't exist yet, and set interested_div at
    // the same time
    if ((interested_div = $j("#"+prefs_ts_div_by_priority(timeslot_id, false))).length == 0)
    {
	// Create the div
	interested_div = $j("<p id='" + prefs_ts_div_by_priority(timeslot_id, false) + "'></p>");
	// Give it a title
	timeslot_div.append("<p><u>Interested classes:</u></p>");
	timeslot_div.append(interested_div);
    }
	

    // Check if the priority div doesn't exist yet, and set priority_div at the
    // same time
    if ((priority_div = $j("#"+prefs_ts_div_by_priority(timeslot_id, true))).length == 0)
    {
	// Create the div
	priority_div = $j("<p id='" + prefs_ts_div_by_priority(timeslot_id, true) + "'></p>");
	// Give it a title
	timeslot_div.append("<p><u>Priority flagged classes:</u></p>");
	timeslot_div.append(priority_div);
    }



    // Make a local reference to the sections for readability
    data_starting_sections = data.timeslots[timeslot_index].starting_sections;
    priority_sections = [];
    interested_sections = [];
    for(i in data_starting_sections)
    {
	if(data.sections[data_starting_sections[i]].lottery_priority)
	{
	    priority_sections.push(data_starting_sections[i]);
	}
	if(data.sections[data_starting_sections[i]].lottery_interested)
	{
	    interested_sections.push(data_starting_sections[i]);
	}
    }

    // Render all the priority classes
    if (priority_sections.length > 0)
    {
	priority_div.html('');
	for (i in priority_sections)
	{
	    render_class_section(data, priority_div, priority_sections[i]);
	}
    }
    else
    {
	// Write "(None)" if there are no classes
	priority_div.html("<i><font color='red'>(None)<br/></font></i>");
    }
    priority_div.append("<br/><br/>");

    // Render all the interested classes
    if (interested_sections.length > 0)
    {
	interested_div.html('');
	for (j in interested_sections)
	{
	    render_class_section(data, interested_div, interested_sections[j]);
	}
    }
    else
    {
	// Write "(None)" if there are no classes
	interested_div.html("<i><font color='red'>(None)<br/></font></i>");
    }
    interested_div.append("<br/>");
    
}

// Append a submit button
function add_submit_button(container_div)
{
    container_div.append("<button id='submit_button' onclick=\"submit_preferences()\" >Save my preferences!</button>");
}
	

function submit_preferences(){
    $j("#submit_button").text("Submitting...");
    $j("#submit_button").attr("disabled", "disabled");

    submit_data = {};
    for(id in sections){
	s = sections[id];
	submit_data[id] = s['lottery_interested'];
	submit_data['flag_'+id] = s['lottery_priority']; 
    }
    
    submit_data_string = JSON.stringify(submit_data);

    var submit_url = '/learn/'+base_url+'/lsr_submit';

    //actually submit and redirect to student reg
    jQuery.ajax({
	     type: 'POST',
             url: submit_url,
	     error: function(a, b, c) {
                alert("There has been an error on the website. Please contact " + support + " to report this problem.");
             },
	     success: function(a, b, c){
		alert("Your preferences have been successfully saved.");
		window.location = "studentreg";
	     },
	     data: {'json_data': submit_data_string },
	     headers: {'X-CSRFToken': $j.cookie("esp_csrftoken")}
     });
};
    
// Create all the preferences in the div with id="preferences" if they don't already exist
function update_preferences(data)
{
    var preferences_div = $j("#preferences");

    for (timeslot in data.timeslots)
    {
	update_timeslot_prefs(data, preferences_div, data.timeslots[timeslot].id);
    }

    if ($j("#submit_button").length == 0)
    {
	add_submit_button(preferences_div);
    }
}

