/**    timeslots: map (id) -> JS object with attributes id, label, start, end, sections (list of IDs)
       sections: map (id) -> JS object with attributes id, emailcode, title, timeslots (sorted list of IDs), grade_min, grade_max, capacity, num_students, lottery_priority, lottery_interested **/
	
var accordionSettings;	

$j(document).ready(function() { 
    $j("#timeslots_anchor").html("Loading timeslots... <br/>").css("display", "block");


    // Create the accordion settings
    accordionSettings = {
	header: ".header",
	autoHeight: false,
	changestart: function(event, ui) {
	    if (ui.newContent.attr("id") == "preferences")
	    {
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
    var dateA = new Date(a.start.year, a.start.month, a.start.day, a.start.hour, a.start.minute, a.start.second, 0);
    var dateB = new Date(b.start.year, b.start.month, b.start.day, b.start.hour, b.start.minute, b.start.second, 0);
    if (dateA > dateB){
	return 1;
    }
    return -1;
};

get_timeslot_html = function(timeslot_data)
{
    template = "\
    <h3 class='header'><a href='#'><b>%TIMESLOT_LABEL% </b></a></h3>\
    <div id='%TIMESLOT_DIV%'>\
        <h3>Walk-in Seminars</h3>\
        <div id='%TIMESLOT_WALKIN_DIV%' style='margin:1em 1em 1em 1em'></div>\
\
        <h3>Classes that start in another timeblock</h3>\
        <div id='%TIMESLOT_CARRYOVER_DIV%' style='margin:1em 1em 1em 1em'></div>\
\
        <h3>Regular Classes</h3>\
        <table id='%TIMESLOT_TABLE%' cellspacing='10'>\
            <tr>\
                <td><p>Priority</p></td>\
                <td><p>Interested</p></td>\
                <td><p>Class</p></td>\
            </tr>\
        </table>\
    </div><br>"
        .replace(/%TIMESLOT_ID%/g, timeslot_data['id'])
        .replace(/%TIMESLOT_DIV%/g, ts_div_from_id(timeslot_data['id']))
        .replace(/%TIMESLOT_TABLE%/g, ts_table_from_id(timeslot_data['id']))
        .replace(/%TIMESLOT_WALKIN_DIV%/g, ts_walkin_div_from_id(timeslot_data['id']))
        .replace(/%TIMESLOT_CARRYOVER_DIV%/g, ts_carryover_div_from_id(timeslot_data['id']))
	.replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
    return template;
};

add_classes_to_timeslot = function(timeslot, sections){
    carryover_id_list = t['sections'];
    class_id_list = t['starting_sections'];
    user_grade = esp_user['cur_grade'];

    //adds the "no priority" radio button and defaults it to checked (this will change if we load a different, previously specified preference)
    var no_priority_template = "<tr><td><p><input type=radio name=\"%TS_RADIO_NAME%\" onChange='priority_changed(null, %TIMESLOT_ID%)' id=\"%TS_NO_PREFERENCE_ID%\" checked></input></p></td> <td></td> <td><p>I would not like to specify a priority class for this timeblock.</p></td></tr>";
    no_priority_template = no_priority_template.replace(/%TS_RADIO_NAME%/g, ts_radio_name(timeslot['label']))
	.replace(/%TIMESLOT_ID%/g, timeslot.id)
        .replace(/%TS_NO_PREFERENCE_ID%/g, ts_no_preference_id(timeslot['label']));
    $j("#"+ts_table_from_id(timeslot['id'])).append(no_priority_template);
    //$j("#"+ts_no_preference_id(timeslot['label'])).prop("checked", true);

    //add checkboxes and radio buttons for each class

    var has_walkins = false;
    var has_classes = false;
    var has_carryovers = false;
    var walkins_list = [];
    var classes_list = [];
    var carryovers_list = [];
    for(i in class_id_list){
	id = class_id_list[i];
	section = sections[id];
	
	//grade check
	if(user_grade >= section['grade_min'] && user_grade <= section['grade_max'] ){
	    if(section['emailcode'].charAt(0) != 'W'){
		has_classes = true;
		classes_list.push(section);
	    }
	}
    }

    for(i in carryover_id_list){
	id = carryover_id_list[i];
	section = sections[id];

	//grade check
	if(user_grade >= section['grade_min'] && user_grade <= section['grade_max'] ){
	    if(section['emailcode'].charAt(0) == 'W'){
		has_walkins = true;
		walkins_list.push(section);
	    }
	    else if($j.inArray(section, classes_list) == -1){
		has_carryovers = true;
		carryovers_list.push(section);
	    }
	}
    }


    //add all the classes then walkins
    if(!has_walkins){
	//hopefully nobody will ever see this :)
	$j("#"+ts_walkin_div_from_id(timeslot['id'])).append("<i><font color='red'>(No walk-ins)</font></i>");
    }
    else{
	for(i in walkins_list){
	    $j("#"+ts_walkin_div_from_id(timeslot['id'])).append(get_walkin_html(walkins_list[i], timeslot['id']));
	}
    }
    if(!has_classes){
	//hopefully nobody will ever see this either :)
	$j("#"+ts_div_from_id(timeslot['id'])).append("<i><font color='red'>(No classes)</font></i>");
    }
    else{
	for(i in classes_list){
	    $j("#"+ts_table_from_id(timeslot['id'])).append(get_class_checkbox_html(classes_list[i], timeslot['id']));
	    load_old_preferences(classes_list[i]);
	}
    }
    if(!has_carryovers){
	$j("#"+ts_carryover_div_from_id(timeslot['id'])).append("<i><font color='red'>(No carry-overs)</font></i>");
    }
    else{
	for(i in carryovers_list){
	    $j("#"+ts_carryover_div_from_id(timeslot['id'])).append(get_carryover_html(carryovers_list[i], timeslot['id']));
	}
    }

};

get_class_checkbox_html = function(class_data, timeslot_id){
    template = "<tr><td><p><input type=radio onChange='priority_changed(%CLASS_ID%, %TIMESLOT_ID%)' id=\"%CLASS_RADIO_ID%\" name=\"%TS_RADIO_NAME%\"></input></p></td> <td><p><input type=checkbox onChange='interested_changed(%CLASS_ID%)' name=%CLASS_CHECKBOX_ID% id=%CLASS_CHECKBOX_ID%></checkbox></p></td> <td><p>%CLASS_EMAILCODE%: %CLASS_TITLE%</p></td></tr>"
	.replace(/%TIMESLOT_ID%/g, timeslot_id)
        .replace(/%TS_RADIO_NAME%/g, ts_radio_name(timeslots[timeslot_id].label))
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title'])
        .replace(/%CLASS_ID%/g, class_data['id'])
        .replace(/%CLASS_CHECKBOX_ID%/g, class_checkbox_id(class_data['id']))
        .replace(/%CLASS_RADIO_ID%/g, class_radio_id(class_data['id']));
    return template;
};

get_walkin_html = function(class_data, timeslot_id){
    template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE%</p>"
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title']);
    return template;
};

get_carryover_html = function(class_data, timeslot_id){
    template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE%</p>"
	.replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
	.replace(/%CLASS_TITLE%/g, class_data['title']);
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
    for (i in timeslots[timeslot_id].starting_sections){
	    sections[timeslots[timeslot_id].starting_sections[i]]['lottery_priority'] = false;
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

ts_walkin_div_from_id = function(id){
    return "TS_W_"+id;
};

ts_carryover_div_from_id = function(id){
    return "TS_C_"+id;
};

ts_table_from_id = function(id){
    return "TS_TABLE_"+id;
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
