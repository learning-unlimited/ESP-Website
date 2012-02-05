//the following is temporary sample data until json queries are actually constructed

/**    timeslots: map (id) -> JS object with attributes id, label, start, end, sections (list of IDs)
       sections: map (id) -> JS object with attributes id, emailcode, title, timeslots (sorted list of IDs), grade_min, grade_max, capacity, num_students, lottery_priority, lottery_interested **/

timeslots = {1:  
	     {
		 id: 1, 
		 label: "Sat 9-10",
		 sections: [1, 2]  
	     },

	     2:
	     {
		 id: 2,
		 label: "Sat 10-11",
		 sections: [3, 4]
	     }
         }

sections = {
    1:
    {
	id: 1,
	emailcode: "M1234",
	    title: "A two-slot math class",
	    timeslots: [1, 2],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: false,
	    lottery_interested: false
    },

 2:
    {
	id: 2,
	emailcode: "M1235",
	    title: "A one-slot math class, 9-12",
	    timeslots: [1],
	    grade_min: 9,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: false,
	    lottery_interested: false
	    },
 3:
    {
	id: 3,
	emailcode: "A2222",
	    title: "An arts class iwth interest",
	    timeslots: [2],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: false,
	    lottery_interested: true
	    },
 4:
    {
	id: 4,
	emailcode: "A3333",
	    title: "An arts class with priority",
	    timeslots: [2],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: true,
	    lottery_interested: false
    }
}

$j(document).ready(function() { 
    data_components = [
        'timeslots',
        'sections',
        'lottery_preferences'
    ];
    json_fetch(data_components, function (data) {test_data = data; console.log("Completed initial data fetch"); show_app(data);});

});              

show_app = function(timeslots){
    //should display a list of timeslots as hyperlinks 
    //and some instructions in a div that we will replace with checkboxes
 
    //adds timeslot links to page
    for(id in timeslots){
	t = timeslots[id];
	$j("#lsr_content").append(get_timeslot_html(t));
    }
};

get_timeslot_html = function(timeslot_data)
{
    template = "<a href='#' onclick='$j(\"#%TIMESLOT_ID%\").slideToggle(); return false;'><b>%TIMESLOT_LABEL% </b></a> <div id='%TIMESLOT_ID%'></div><br>";
    template = template.replace(/%TIMESLOT_ID%/g, 'TS_' + timeslot_data['id']).replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
    return template;
}


show_timeslot = function(id){
    /*t = timeslots[id];
    class_id_list = t['sections'];

    //add checkboxes and radio buttons for each class
    for(i in class_id_list){
	id = class_id_list[i];
	console.log();
	$j("#lsr_content").append(get_class_checkbox_html(sections[id], t['label']));
	}*/
};

get_class_checkbox_html = function(class_data, timeslot_name){
    console.log(class_data);
    template = "<input type=radio name=%TIMESLOT%_priority value=%PRIORITY%></input> <input type=checkbox name=%CLASS_ID%_interested></checkbox> %CLASS_ID%: %CLASS_TITLE%<br>";
    template = template.replace("%TIMESLOT%", timeslot_name).replace("%PRIORITY%", class_data['lottery_priority']).replace(/%CLASS_ID%/g, class_data['emailcode'])
    .replace('%CLASS_TITLE%', class_data['title']);
    console.log(template);
    return template;
};
