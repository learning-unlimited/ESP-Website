// Example data for testing, normally this would be set globally by the JSON views API
data = {
    timeslots: [
	{
	    id: 0,
	    label: "9AM",
	    start: 9,
	    end: 10,
	    sections: [0, 1]
	},
	{
	    id: 1,
	    label: "10AM",
	    start: 10,
	    end: 11,
	    sections: [2]
	}
    ],
    sections: [
	{
	    id: 0,
	    emailcode: "A1",
	    title: "Winrar: An Introduction",
	    timeslots: [0],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 100,
	    num_students: 20,
	    lottery_priority: true,
	    lottery_interested: false
	},
	{
	    id: 1,
	    emailcode: "A2",
	    title: "Winrar: An Introduction",
	    timeslots: [1],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 100,
	    num_students: 20,
	    lottery_priority: false,
	    lottery_interested: false
	},
	{
	    id: 2,
	    emailcode: "B1",
	    title: "How to be Awesome",
	    timeslots: [0, 1],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 100,
	    num_students: 20,
	    lottery_priority: true,
	    lottery_interested: true
	}
    ]
};


// Appends an individual class section to the containerDiv
function renderClassSection(containerDiv, classSection)
{
    containerDiv.append(data.sections[classSection].emailcode + ": " + data.sections[classSection].title + "<br />");
}

// Appends the block of priority preferences followed by the interested
// preferences for a given timeblock
function renderTimeblockPrefs(containerDiv, timeslotIndex)
{
    containerDiv.append("<h2>" + data.timeslots[timeslotIndex].label + "</h2><br/>");
    sections = data.timeslots[timeslotIndex].sections;
    prioritySections = [];
    interestedSections = [];
    for(var i = 0; i < sections.length; i++)
    {
	if(data.sections[sections[i]].lottery_priority)
	{
	    prioritySections.push(sections[i]);
	}
	if(data.sections[sections[i]].lottery_interested)
	{
	    interestedSections.push(sections[i]);
	}
    }

    // Priority classes
    containerDiv.append("<b>Priority flagged classes:<br/></b>");
    if (prioritySections.length > 0)
    {
	// Render all the priority classes
	for (var i = 0; i < prioritySections.length; i++)
	{
	    renderClassSection(containerDiv, prioritySections[i]);
	}
    }
    else
    {
	// Write "(None)" if there are no classes
	containerDiv.append("<i><font color='red'>(None)<br/></font></i>");
    }
    containerDiv.append("<br/>");


    // Interested classes
    containerDiv.append("<b>Interested classes:<br /></b>");
    if (interestedSections.length > 0)
    {
	// Render all the interested classes
	for (var j = 0; j < interestedSections.length; j++)
	{
	    renderClassSection(containerDiv, interestedSections[j]);
	}
    }
    else
    {
	// Write "(None)" if there are no classes
	containerDiv.append("<i><font color='red'>(None)<br/></font></i>");
    }
    containerDiv.append("<br /><br />");
}
	
    
// Create all the preferences in the div with id="preferences"
function renderPreferences()
{
    var preferencesDiv = $j("#preferences");

    for (var i = 0; i < data.timeslots.length; i++)
    {
	renderTimeblockPrefs(preferencesDiv, data.timeslots[i].id);
    }
}

/*
TODO: This gets triggered too early for some reason... fix this and then use it instead
$j(document).ready()
{
    console.log("Document ready");
    renderPreferences();
}
*/