/**    timeslots: map (id) -> JS object with attributes id, label, start, end, sections (list of IDs)
       sections: map (id) -> JS object with attributes id, emailcode, title, timeslots (sorted list of IDs), grade_min, grade_max, capacity, num_students, lottery_priority, lottery_interested **/
	
$j(document).ready(function() {
    $j("#timeslots_anchor").html("Loading timeslots... <br/>").css("display", "block");

    jquery_ui_init();

    data_components = [
        'timeslots',
        'sections',
        'lottery_preferences'
    ];

    json_fetch(data_components, show_app, null, fail_gracefully);
});


var accordion_settings;	

// Initializes various jQuery UI things
jquery_ui_init = function(){

    // Create the accordion settings
    accordion_settings = {
	// Class 'header' elements will be considered headers by the accordion
	header: ".header",
	autoHeight: false,
	collapsible: true,
	changestart: function(event, ui) {
	    // If we're switching to the preferences tab, update it
	    if (ui.newContent.attr("id") == "preferences")
	    {
		update_preferences({'timeslots': timeslots, 'sections': sections});
	    }
	}
    };

    // Initialize the lsr_content div to an accordion
    $j("#lsr_content").accordion(accordion_settings);
};

//returns 1 if a starts after b, and -1 otherwise
//for use sorting timeslots by start time
compare_timeslot_starts = function(a, b){
    var dateA = new Date(a.start[0], a.start[1], a.start[2], a.start[3], a.start[4], a.start[5], 0);
    var dateB = new Date(b.start[0], b.start[1], b.start[2], b.start[3], b.start[4], b.start[5], 0);

    if (dateA > dateB){
	return 1;
    }
    return -1;
};

// adds timeslots to content and adds classes to timeslots
// called once class data arrives from the server
show_app = function(data){
    timeslots = data['timeslots'];
    sections = data['sections'];
    timeslot_objects = [];

    //initialize array which will hold the class id of the last clicked class priority radio
    last_priority = {};

    //creates a list of the timeslots sorted by start time
    sorted_timeslots = [];
    for(id in timeslots){
	sorted_timeslots.push(timeslots[id]);
    }
    sorted_timeslots.sort(compare_timeslot_starts);

    //adds timeslot links to page
    $j("#timeslots_anchor").css("display", "none");
    for(index in sorted_timeslots){
	ts = new Timeslot(sorted_timeslots[index]);
	timeslot_objects.push(ts);
	$j("#timeslots_anchor").before(ts.get_timeslot_html());
	ts.add_classes_to_timeslot(sections);//needs to be updated w/ object-orientedness
    }

    //recreate the accordion now to update for the timeslots
    $j("#lsr_content").accordion('destroy').accordion(accordion_settings);
};
