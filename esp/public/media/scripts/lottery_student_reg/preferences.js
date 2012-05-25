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


// Append a submit button
function add_submit_button(container_div)
{
    container_div.append("<button id='submit_button' onclick=\"submit_preferences()\" >Save my preferences!</button>");
}

    
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

