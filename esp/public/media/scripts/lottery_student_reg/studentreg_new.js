
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
    template = "<input type=radio name=%TIMESLOT%_priority value=%PRIORITY%></input> <input type=checkbox name=%CLASS_ID%_interested></checkbox> %CLASS_ID%: %CLASS_TITLE%<br>";
    template = template.replace("%TIMESLOT%", timeslot_name).replace("%PRIORITY%", class_data['lottery_priority']).replace(/%CLASS_ID%/g, class_data['emailcode'])
    .replace('%CLASS_TITLE%', class_data['title']);
    return template;
};

ts_div_from_id = function(id){
    return "TS_"+id;
};

show_timeslot = function(id){
    $j("#"+ts_div_from_id(id)).slideToggle();
};
