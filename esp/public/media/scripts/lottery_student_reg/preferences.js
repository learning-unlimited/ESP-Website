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
    container_div.append(sections[class_section].emailcode + "s" + sections[class_section].index + ": " + sections[class_section].title + "<br/>");
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

    var ts;
    for (ts in timeslot_objects)
    {		   
      	timeslot_objects[ts].update_timeslot_prefs(preferences_div);
    }

    if ($j("#submit_button").length == 0)
    {
	add_submit_button(preferences_div);
    }
}

