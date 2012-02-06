
/**    timeslots: map (id) -> JS object with attributes id, label, start, end, sections (list of IDs)
       sections: map (id) -> JS object with attributes id, emailcode, title, timeslots (sorted list of IDs), grade_min, grade_max, capacity, num_students, lottery_priority, lottery_interested **/


$j(document).ready(function() { 
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

    //adds timeslot links to page
    for(id in timeslots){
	t = timeslots[id];
	$j("#lsr_content").append(get_timeslot_html(t));
	add_classes_to_timeslot(t, sections);
    }
};

get_timeslot_html = function(timeslot_data)
{
    template = "<a onclick='show_timeslot(%TIMESLOT_ID%)'><b>%TIMESLOT_LABEL% </b></a> <div id='%TIMESLOT_DIV%' hidden=true></div><br>";
    template = template.replace(/%TIMESLOT_ID%/g, timeslot_data['id']).replace(/%TIMESLOT_DIV%/g, ts_div_from_id(timeslot_data['id'])).replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
    return template;
};

add_classes_to_timeslot = function(timeslot, sections){
    class_id_list = t['sections'];
    user_grade = esp_user['cur_grade'];

    //add checkboxes and radio buttons for each class
    for(i in class_id_list){
	id = class_id_list[i];
	section = sections[id];

	//walkins check
	if(section['emailcode'].charAt(0) != 'W'){
	    //grade check
	    if(user_grade >= section['grade_min'] && user_grade <= section['grade_max'] ){
		$j("#"+ts_div_from_id(timeslot['id'])).append(get_class_checkbox_html(section, t['label']));
	    }
	}
    }
};

get_class_checkbox_html = function(class_data, timeslot_name){
    template = "<input type=radio onChange='priority_changed(%CLASS_ID%, \"%TIMESLOT%\")' name=\"%TIMESLOT%_priority\" value=%PRIORITY%></input> <input type=checkbox onChange='interested_changed(%CLASS_ID%)' name=%CLASS_ID%_interested></checkbox> %CLASS_EMAILCODE%: %CLASS_TITLE%<br>";
    template = template.replace(/%TIMESLOT%/g, timeslot_name).replace("%PRIORITY%", class_data['lottery_priority']).replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
    .replace('%CLASS_TITLE%', class_data['title']).replace(/%CLASS_ID%/g, class_data['id']);
    return template;
};

priority_changed = function(id, timeslot){
    //unprioritize previous selection
    if(last_priority[timeslot]){
	sections[last_priority[timeslot]]['lottery_priority'] = false;
    }
    //prioritize this selection
    sections[id]['lottery_priority'] = true;
    //remember this selection 
    last_priority[timeslot] = id;
};

interested_changed = function(id){
    sections[id]['lottery_interested'] = !sections[id]['lottery_interested'];
};

ts_div_from_id = function(id){
    return "TS_"+id;
};

class_radio_id = function(id){
    return "class_radio_" + id;
};

show_timeslot = function(id){
    $j("#"+ts_div_from_id(id)).slideToggle();
};
