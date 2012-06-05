
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

    user_grade = esp_user['cur_grade'];

    json_fetch(data_components, show_app);
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
    var dateA = new Date(a.start.year, a.start.month, a.start.day, a.start.hour, a.start.minute, a.start.second, 0);
    var dateB = new Date(b.start.year, b.start.month, b.start.day, b.start.hour, b.start.minute, b.start.second, 0);
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

function get_carryover_html(class_data, add_link){
    // Create a carried-over class div using a template with keywords replaced below
    template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE% ";
    if (add_link){
	template = template + "[<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]";
    }
    template = template + "</p>";
    template = template.replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
    .replace(/%CLASS_TITLE%/g, class_data['title'])
    .replace(/%CLASS_ID%/g, class_data['id']);
    return template;
};


function submit_preferences(){
    $j("#submit_button").text("Submitting...");
    $j("#submit_button").attr("disabled", "disabled");

    var submit_data = get_submit_data();

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
	     headers: {'X-CSRFToken': $j.cookie("csrftoken")}
     });
};

