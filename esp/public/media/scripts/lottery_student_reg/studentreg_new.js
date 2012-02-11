
/**    timeslots: map (id) -> JS object with attributes id, label, start, end, sections (list of IDs)
       sections: map (id) -> JS object with attributes id, emailcode, title, timeslots (sorted list of IDs), grade_min, grade_max, capacity, num_students, lottery_priority, lottery_interested **/
	
var accordionSettings;	

$j(document).ready(function() { 
    $j("#timeslots_anchor").html("Loading timeslots... <br/>").css("display", "block");


    // Create the accordion settings
    accordionSettings = {
	header: "a.header",
	autoHeight: false,
	changestart: function(event, ui) {
	    if (ui.newContent.attr("id") == "preferences")
	    {
		console.log("Updating preferences");
		updatePreferences({'timeslots': timeslots, 'sections': sections});
	    }
	}
    };

    $j("#lsr_content").accordion(accordionSettings);

    data_components = [
        'timeslots',
        'sections',
        'lottery_preferences'
    ];

    json_fetch(data_components, show_app);
});

// adds timeslots to content and adds classes to timeslots
// called once class data arrives from the server
show_app = function(data){
    timeslots = data['timeslots'];
    sections = data['sections'];


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
	t = sorted_timeslots[index];
	$j("#timeslots_anchor").before(get_timeslot_html(t));
	add_classes_to_timeslot(t, sections);
    }

    //recreate the accordion now to update for the timeslots
    $j("#lsr_content").accordion('destroy').accordion(accordionSettings);
};

//returns 1 if a starts after b, and -1 otherwis.
//for use sorting timeslots by start time
compare_timeslot_starts = function(a, b){
    var dateA = new Date(a['start']);
    var dateB = new Date(b['start']);
    if (dateA > dateB){
	return 1;
    }
    return -1;
};

get_timeslot_html = function(timeslot_data)
{
    template = "<a href='#' class='header'><b>%TIMESLOT_LABEL% </b></a> <div id='%TIMESLOT_DIV%'></div><br>";
    template = template.replace(/%TIMESLOT_ID%/g, timeslot_data['id']).replace(/%TIMESLOT_DIV%/g, ts_div_from_id(timeslot_data['id'])).replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
    return template;
};

add_classes_to_timeslot = function(timeslot, sections){
    class_id_list = t['sections'];
    user_grade = esp_user['cur_grade'];

    //adds the "no priority" radio button and defaults it to checked (this will change if we load a different, previously specified preference)
    var no_priority_template = "<input type=radio name=\"%TS_RADIO_NAME%\" onChange='priority_changed(null, %TIMESLOT_ID%)' id=\"%TS_NO_PREFERENCE_ID%\" checked></input> I would not like to specify a priority class for this timeblock.<br/>";
    no_priority_template = no_priority_template.replace(/%TS_RADIO_NAME%/g, ts_radio_name(timeslot['label']))
	.replace(/%TIMESLOT_ID%/g, timeslot.id)
        .replace(/%TS_NO_PREFERENCE_ID%/g, ts_no_preference_id(timeslot['label']));
    $j("#"+ts_div_from_id(timeslot['id'])).append(no_priority_template);
    //$j("#"+ts_no_preference_id(timeslot['label'])).prop("checked", true);

    //add checkboxes and radio buttons for each class
    if (Object.keys(class_id_list).length > 0){
	for(i in class_id_list){
	    id = class_id_list[i];
	    section = sections[id];
	    
	    //walkins check
	    if(section['emailcode'].charAt(0) != 'W'){
		//grade check
		if(user_grade >= section['grade_min'] && user_grade <= section['grade_max'] ){
		    $j("#"+ts_div_from_id(timeslot['id'])).append(get_class_checkbox_html(section, t['id']));
		    load_old_preferences(section);
 		}
	    }
	}
    }
    else{
	//hopefully nobody will ever see this :)
	$j("#"+ts_div_from_id(timeslot['id'])).append("<i><font color='red'>(No classes)</font></i>");
    }
};

get_class_checkbox_html = function(class_data, timeslot_id){
    template = "<input type=radio onChange='priority_changed(%CLASS_ID%, %TIMESLOT_ID%)' id=\"%CLASS_RADIO_ID%\" name=\"%TS_RADIO_NAME%\"></input> <input type=checkbox onChange='interested_changed(%CLASS_ID%)' name=%CLASS_CHECKBOX_ID% id=%CLASS_CHECKBOX_ID%></checkbox>  %CLASS_EMAILCODE%: %CLASS_TITLE%<br>";
    template = template.replace(/%TIMESLOT_ID%/g, timeslot_id)
        .replace(/%TS_RADIO_NAME%/g, ts_radio_name(timeslots[timeslot_id].label))
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title'])
        .replace(/%CLASS_ID%/g, class_data['id'])
        .replace(/%CLASS_CHECKBOX_ID%/g, class_checkbox_id(class_data['id']))
        .replace(/%CLASS_RADIO_ID%/g, class_radio_id(class_data['id']));
    return template;
};

load_old_preferences = function(class_data){
    id = class_data['id'];
    if( class_data['lottery_priority'] )
    {
	$j("#"+class_radio_id(id)).prop("checked", true);
    }
    if( class_data['lottery_interested'] )
    {
	$j("#"+class_checkbox_id(id)).prop("checked", true);
    }
};

priority_changed = function(id, timeslot_id){
    //unprioritize all selections
    for (i in timeslots[timeslot_id].sections){
	sections[timeslots[timeslot_id].sections[i]]['lottery_priority'] = false;
    }

    if(id){
	//prioritize this selection
	sections[id]['lottery_priority'] = true;
	//remember this selection 
    }
};


interested_changed = function(id){
    sections[id]['lottery_interested'] = !sections[id]['lottery_interested'];
};

ts_div_from_id = function(id){
    return "TS_"+id;
};

ts_radio_name = function(ts_name){
    return ts_name + '_priority';
};

ts_no_preference_id = function(ts_name){
    return ts_name + '_no_preference';
};

class_radio_id = function(id){
    return "class_radio_" + id;
};

class_checkbox_id = function(id){
    return "interested_"+ id;
};

show_timeslot = function(id){
    $j("#"+ts_div_from_id(id)).slideToggle();
};
