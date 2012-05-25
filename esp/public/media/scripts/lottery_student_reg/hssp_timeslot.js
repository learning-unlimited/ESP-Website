var Timeslot = function(data){
    var timeslot_data = data;
    var timeslot_id = data['id'];

    var priority_limit = 3;

    //some div ids
    var ts_div = "TS_"+data["id"];
    var ts_table_div = "TS_TABLE_" + data["id"];

    this.get_timeslot_html = function()
    {
	// Create some html for the timeslot, making use of keywords which are
	// replaced by values below
	template = "\
    <h3 class='header'><a href='#'><b>%TIMESLOT_LABEL% </b></a></h3>	\
    <div id='%TIMESLOT_DIV%'>						\
        <h3>Regular Classes</h3>\
        <table id='%TIMESLOT_TABLE%' cellspacing='10' width='100%'>\
        </table>\
    </div><br>";
	template = template.replace(/%TIMESLOT_ID%/g, timeslot_data['id']);
	template = template.replace(/%TIMESLOT_DIV%/g, ts_div);
	template = template.replace(/%TIMESLOT_TABLE%/g, ts_table_div);
	template = template.replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
	return template;
    };

    this.add_classes_to_timeslot = function(sections){
	class_id_list = timeslot_data['starting_sections'];
	user_grade = esp_user['cur_grade'];

	//construct list of classes
	var classes_list = [];
	for(i in class_id_list){
	    class_id = class_id_list[i];
	    section = sections[class_id];
	    // check grade in range or admin
	    if((user_grade >= section['grade_min'] && user_grade <= section['grade_max']) || esp_user['cur_admin'] == 1){
		if (section['status'] > 0)
		    {
			has_classes = true;
			classes_list.push(section);
		    }
	    }
	}

	// Add classes (starting in this timeblock) section
	if(!has_classes){
	    //hopefully nobody will ever see this either :)
	    $j("#"+ ts_div).append("<i><font color='red'>(No classes)</font></i>");
	}
	else{
	    // Adds all classes that start in this timeblock
	    for(i = 1; i <=priority_limit; i++){
		class_checkbox = new this.ClassCombobox(classes_list, i);
		class_checkbox.add_self_to_timeslot();
	    }
	}
	// Add carried over classes section
    };

    //class checkboxes
    this.ClassCombobox = function(class_data, priority){
	var combobox_id = "combobox_" + timeslot_id + "_" + priority;

	// Callback for when a priority radio is changed
	priority_changed = function(){
	    // Unprioritize all selections in the timeblock
	    for (i in timeslot_data['starting_sections']){
		sections[timeslot_data['starting_sections'][i]]['Priority/' + priority] = false;
	    }

	    if(class_id){
		// Prioritize this selection
		sections[class_id]['Priority/'+ priority] = true;
	    }
	};
	
	// Function to populate a class div with existing preference data
	this.load_old_preferences = function(){
	};

	this.add_self_to_timeslot = function(){
	    $j("#"+ts_table_div).append(this.get_combobox_html());
	    $j("#"+combobox_id).append("<option> No Class");
	    for(j in class_data){
		$j("#"+combobox_id).append(this.get_class_html(class_data[j]));
	    }
	    $j("#"+combobox_id).on("click", priority_changed);
	    this.load_old_preferences()
	};

	this.get_class_html = function(class_data){
	    var display_name = class_data['emailcode'] + ": " + class_data['title'];
	    var template = "<option value=%CLASS_ID%> %CLASS_TITLE%"
	    .replace(/%CLASS_ID%/g, class_data['id'])
	    .replace(/%CLASS_TITLE%/, display_name);
	    return template;
	};

        this.get_combobox_html = function(){
	    // Create the class div using a template that has keywords replaced with values below
	    template = "<tr>\
        <td><p>\
            Choice %PRIORITY%:\
        </p></td>\
        <td><p>\
            <select id=\"%COMBOBOX_ID%\"\>\
            </select>\
        </p></td>\
    </tr>"
	    .replace(/%COMBOBOX_ID%/g, combobox_id)
	    .replace(/%PRIORITY%/g, priority);
	    return template;
	};
    }
};

// Appends the slot of priority preferences followed by the interested
// preferences for a given timeslot
function update_timeslot_prefs(data, container_div, timeslot_index)
{
    var timeslot_id = data.timeslots[timeslot_index].id;

    // Check to see if the timeslot div doesn't exist,
    // and set timeslot_div at the same time
    if ((timeslot_div = $j("#"+prefs_ts_div_from_id(timeslot_id))).length == 0)
    {
	// Create the div
	timeslot_div = $j("<div id='" + prefs_ts_div_from_id(timeslot_id) + "'></div>");
	container_div.append(timeslot_div);
	// Create the title
	timeslot_div.append("<h3>" + data.timeslots[timeslot_index].label + "</h3><br/>");
    }

    data_starting_sections = data.timeslots[timeslot_index].starting_sections;
    //create divs for priority 1, 2, and 3
    for (p = 1; p <= 3; p++){
	// Check if the interested div doesn't exist yet, and set interested_div at
	// the same time
	if ($j("#"+prefs_ts_div_by_priority(timeslot_id, p)).length == 0)
	    {
		// Create the div
		interested_div = $j("<p id='" + prefs_ts_div_by_priority(timeslot_id, p) + "'></p>");
		// find the class with this priority
		var has_priority_class = false;
		for(i in data_starting_sections){
		   
		}
		timeslot_div.append("<p><u>Choice "+ p +"</u></p>");	       
		timeslot_div.append(interested_div);
		if (has_priority_class == true){
		    render_class_section(data, interested_div, priority_class);
		}
		else{
		    //nasty message about not having a class with this priority  
		}
	    }
    }    
}
	

//needs to be written
function submit_preferences(){
};

