// Generates a unique div id based on the timeslot id
function prefs_ts_div_from_id(id)
{
    return "pref_TS_"+id;
}
function prefs_ts_div_by_priority(id, priority)
{
    return prefs_ts_div_from_id(id) + (priority ? "_p" : "_i");
} 

// Appends an individual class section to the containerDiv
function renderClassSection(data, containerDiv, classSection)
{
    containerDiv.append(data.sections[classSection].emailcode + ": " + data.sections[classSection].title + "<br />");
}

// Appends the slot of priority preferences followed by the interested
// preferences for a given timeslot
function updateTimeslotPrefs(data, containerDiv, timeslotIndex)
{
    var timeslotId = data.timeslots[timeslotIndex].id;

    // Check to see if the timeslot div doesn't exist,
    // and set timeslotDiv at the same time
    if ((timeslotDiv = $j("#"+prefs_ts_div_from_id(timeslotId))).length == 0)
    {
	// Create the div
	timeslotDiv = $j("<div id='" + prefs_ts_div_from_id(timeslotId) + "'></div>");
	containerDiv.append(timeslotDiv);
	// Create the title
	timeslotDiv.append("<h3>" + data.timeslots[timeslotIndex].label + "</h3><br/>");
    }

    // Check if the interested div doesn't exist yet, and set interestedDiv at
    // the same time
    if ((interestedDiv = $j("#"+prefs_ts_div_by_priority(timeslotId, false))).length == 0)
    {
	// Create the div
	interestedDiv = $j("<div id='" + prefs_ts_div_by_priority(timeslotId, false) + "'></div.");
	// Give it a title
	timeslotDiv.append("<b>Interested classes:<br /></b>");
	timeslotDiv.append(interestedDiv);
    }
	

    // Check if the priority div doesn't exist yet, and set priorityDiv at the
    // same time
    if ((priorityDiv = $j("#"+prefs_ts_div_by_priority(timeslotId, true))).length == 0)
    {
	// Create the div
	priorityDiv = $j("<div id='" + prefs_ts_div_by_priority(timeslotId, true) + "'></div>");
	// Give it a title
	timeslotDiv.append("<b>Priority flagged classes:<br/></b>");
	timeslotDiv.append(priorityDiv);
    }



    // Make a local reference to the sections for readability
    data_sections = data.timeslots[timeslotIndex].sections;
    prioritySections = [];
    interestedSections = [];
    for(i in data_sections)
    {
	if(data.sections[data_sections[i].id].lottery_priority)
	{
	    prioritySections.push(data_sections[i].id);
	}
	if(data.sections[data_sections[i].id].lottery_interested)
	{
	    interestedSections.push(data_sections[i].id);
	}
    }

    // Render all the priority classes
    if (prioritySections.length > 0)
    {
	priorityDiv.html('');
	for (i in prioritySections)
	{
	    renderClassSection(data, priorityDiv, prioritySections[i]);
	}
    }
    else
    {
	// Write "(None)" if there are no classes
	priorityDiv.html("<i><font color='red'>(None)<br/></font></i>");
    }
    priorityDiv.append("<br/>");

    // Render all the interested classes
    if (interestedSections.length > 0)
    {
	interestedDiv.html('');
	for (j in interestedSections)
	{
	    renderClassSection(data, interestedDiv, interestedSections[j]);
	}
    }
    else
    {
	// Write "(None)" if there are no classes
	interestedDiv.html("<i><font color='red'>(None)<br/></font></i>");
    }
    interestedDiv.append("<br /><br />");
    
}

// Append a submit button
function addSubmitButton(containerDiv)
{
    containerDiv.append("<button id='submitButton' onclick=\"submit_preferences()\" >Save my preferences!</button>");
}
	

function submit_preferences(){
    $j("#submitButton").text("Submitting...");

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
                alert("There has been an error on the website. Please contact esp@mit.edu to report this problem.");
             },
	     success: function(a, b, c){
		alert("Your preferences have been successfuly saved.");
		window.location = "studentreg";
	     },
	     data: {'json_data': submit_data_string },
	     headers: {'X-CSRFToken': $j.cookie("csrftoken")}
     });
};
    
// Create all the preferences in the div with id="preferences" if they don't already exist
function updatePreferences(data)
{
    var preferencesDiv = $j("#preferences");

    for (timeslot in data.timeslots)
    {
	updateTimeslotPrefs(data, preferencesDiv, data.timeslots[timeslot].id);
    }

    if ($j("#submitButton").length == 0)
    {
	addSubmitButton(preferencesDiv);
    }
}

