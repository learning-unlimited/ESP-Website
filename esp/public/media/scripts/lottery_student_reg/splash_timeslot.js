var open_class_category = 'W';

var Timeslot = function(data){
    var timeslot_data = data;
    var timeslot_id = data['id'];

    //some div ids
    var ts_div = "TS_"+data["id"];
    var ts_table_div = "TS_TABLE_" + data["id"];
    var ts_carryover_div = "TS_C_" + data["id"];
    var ts_walkin_div = "TS_W_" + data["id"];
    var ts_radio_name = data["label"] + "_priority";
    var ts_no_preference_id = data["label"] + "_no_preference";
    var prefs_ts_div = "pref_" + data["id"];
    var prefs_ts_div_by_priority = function(p){
	if(p == true){
 	    return prefs_ts_div + "_flag";
	}
	else{
	    return prefs_ts_div + "_interested";
	}
    };


    this.get_walkin_header_html = function()
    {
	if (open_class_registration) {
	    return "<h3>Walk-in Seminars</h3>\
        <div id='%TIMESLOT_WALKIN_DIV%' style='margin:1em 1em 1em 1em'></div>";
	}
	return "";
    }

    walkin_header_html = this.get_walkin_header_html();

    this.get_timeslot_html = function()
    {
	// Create some html for the timeslot, making use of keywords which are
	// replaced by values below
	template = "\
    <h3 class='header'><a href='#'><b>%TIMESLOT_LABEL% </b></a></h3>	\
    <div id='%TIMESLOT_DIV%'>						\
    " + walkin_header_html + "						\
\
        <h3>Classes that start in another timeblock</h3>		\
        <div id='%TIMESLOT_CARRYOVER_DIV%' style='margin:1em 1em 1em 1em'></div> \
\
        <h3>Regular Classes</h3>\
        <table id='%TIMESLOT_TABLE%' cellspacing='10'>\
            <tr>\
                <td><p>Priority</p></td>\
                <td><p>Interested</p></td>\
                <td><p>Class</p></td>\
            </tr>\
        </table>\
    </div><br>";
	template = template.replace(/%TIMESLOT_ID%/g, timeslot_data['id']);
	template = template.replace(/%TIMESLOT_DIV%/g, ts_div);
	template = template.replace(/%TIMESLOT_TABLE%/g, ts_table_div);
	template = template.replace(/%TIMESLOT_WALKIN_DIV%/g, ts_walkin_div);
	template = template.replace(/%TIMESLOT_CARRYOVER_DIV%/g, ts_carryover_div);
	template = template.replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
	return template;
    };

    this.add_classes_to_timeslot = function(sections){

	// Create the dialog used to show class info
	create_class_info_dialog();

	carryover_id_list = timeslot_data['sections'];
	class_id_list = timeslot_data['starting_sections'];

	//adds the "no priority" radio button and defaults it to checked (this will change if we load a different, previously specified preference)
	var no_priority_template = "\
    <tr>			    \
        <td><p>\
            <input type=radio name=\"%TS_RADIO_NAME%\" onChange='priority_changed(null, %TIMESLOT_ID%)' id=\"%TS_NO_PREFERENCE_ID%\" checked></input>\
        </p></td>\
\
        <td></td>\
        <td><p>I would not like to specify a priority class for this timeblock.</p></td>\
    </tr>";
	no_priority_template = no_priority_template.replace(/%TS_RADIO_NAME%/g, ts_radio_name)
	.replace(/%TIMESLOT_ID%/g, timeslot_id)
        .replace(/%TS_NO_PREFERENCE_ID%/g, ts_no_preference_id);
	$j("#"+ts_table_div).append(no_priority_template);

	//add checkboxes and radio buttons for each class
	var has_walkins = false;
	var has_classes = false;
	var has_carryovers = false;
	var walkins_list = [];
	var classes_list = [];
	var carryovers_list = [];
	for(i in class_id_list){
	    class_id = class_id_list[i];
	    section = sections[class_id];

	    // check grade in range or admin
	    if((user_grade >= section['grade_min'] && user_grade <= section['grade_max']) || esp_user['cur_admin'] == 1){
		if(!open_class_registration || section['category'] != open_class_category){
		    if (section['status'] > 0)
			{
			    has_classes = true;
			    classes_list.push(section);
			}
		}
	    }
	}

	for(i in carryover_id_list){
	    section_id = carryover_id_list[i];
	    section = sections[section_id];

	    //check grade in range or admin
	    if(section['status'] > 0 && user_grade >= section['grade_min'] && user_grade <= section['grade_max'] || esp_user['cur_admin'] == 1){
		if(open_class_registration && section['category'] == open_class_category){
		    has_walkins = true;
		    walkins_list.push(section);
		}
		else if($j.inArray(section, classes_list) == -1){
		    has_carryovers = true;
		    carryovers_list.push(section);
		}
	    }
	}

	// Add walkins section
	if(open_class_registration && !has_walkins){
	    //hopefully nobody will ever see this :)
	    $j("#"+ts_walkin_div).append("<i><font color='red'>(No walk-ins)</font></i>");
	}
	else if (open_class_registration){
	    // Add all the walkins classes
	    for(i in walkins_list){
		$j("#"+ts_walkin_div).append(this.get_walkin_html(walkins_list[i], timeslot_id));
	    }
	}
	// Add classes (starting in this timeblock) section
	if(!has_classes){
	    //hopefully nobody will ever see this either :)
	    $j("#"+ ts_div).append("<i><font color='red'>(No classes)</font></i>");
	}
	else{
	    // Adds all classes that start in this timeblock
	    for(i in classes_list){
		class_checkbox = new this.ClassCheckbox(classes_list[i]);
		class_checkbox.add_self_to_timeslot();
	    }
	}
	// Add carried over classes section
	if(!has_carryovers){
	    $j("#"+ts_carryover_div).append("<i><font color='red'>(No carry-overs)</font></i>");
	}
	else{
	    // Adds all classes that are carried over from the previous timeblock
	    for(i in carryovers_list){
		$j("#"+ts_carryover_div).append(get_carryover_html(carryovers_list[i], true));
	    }
	}
    };

    this.get_walkin_html = function(class_data, timeslot_id){
	// Create a walkin div using a template with keywords replaced below
	template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE% [<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]</p>"
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title'])
        .replace(/%CLASS_ID%/g, class_data['id']);
	return template;
    };

    //class checkboxes
    this.ClassCheckbox = function(data){
	var this_class_data = data;
	var class_id = data['id'];
	var class_radio_id = "class_radio_" + class_id;
	var class_checkbox_id = "interested_" + class_id;

	// Callback for when a priority radio is changed
	priority_changed = function(){
	    // Unprioritize all selections in the timeblock
	    for (i in timeslot_data['starting_sections']){
		sections[timeslot_data['starting_sections'][i]]['lottery_priority'] = false;
	    }

	    if(class_id){
		// Prioritize this selection
		sections[class_id]['lottery_priority'] = true;
	    }
	};

	// Callback for when an interested checkbox is changed
	interested_changed = function(){
	    sections[class_id]['lottery_interested'] = !sections[class_id]['lottery_interested'];
	};
	
	// Function to populate a class div with existing preference data
	this.load_old_preferences = function(){
	    if( this_class_data['lottery_priority'] )
		{
		    $j("#"+class_radio_id).prop("checked", true);
		}
	    if( this_class_data['lottery_interested'] )
		{
		    $j("#"+class_checkbox_id).prop("checked", true);
		}
	};

	this.add_self_to_timeslot = function(){
	    $j("#"+ts_table_div).append(this.get_class_checkbox_html());
	    $j("#"+class_checkbox_id).on("click", interested_changed);
	    $j("#"+class_radio_id).on("click", priority_changed);
	    this.load_old_preferences()
	};

        this.get_class_checkbox_html = function(){
	    // Create the class div using a template that has keywords replaced with values below
	    template = "\
    <tr>\
        <td><p>\
            <input type='radio'\
                   id=\"%CLASS_RADIO_ID%\"\
                   name=\"%TS_RADIO_NAME%\">\
            </input>\
        </p></td>\
        <td><p>\
            <input type='checkbox'\
                   name=%CLASS_CHECKBOX_ID%\
                   id=%CLASS_CHECKBOX_ID%>\
            </input>\
        </p></td>\
        <td><p>%CLASS_EMAILCODE%: %CLASS_TITLE% [<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]</p></td>\
    </tr>"
	    .replace(/%TIMESLOT_ID%/g, timeslot_id)
	    .replace(/%TS_RADIO_NAME%/g, ts_radio_name)
	    .replace(/%CLASS_EMAILCODE%/g, this_class_data['emailcode'])
	    .replace('%CLASS_TITLE%', this_class_data['title'])
	    .replace(/%CLASS_ID%/g, this_class_data['id'])
	    .replace(/%CLASS_CHECKBOX_ID%/g, class_checkbox_id)
	    .replace(/%CLASS_RADIO_ID%/g, class_radio_id);
	    return template;
	};
    };

    // Appends the slot of priority preferences followed by the interested
    // preferences for a given timeslot
    this.update_timeslot_prefs = function(container_div)
    {
	// Check to see if the timeslot div doesn't exist,
	// and set timeslot_div at the same time
	var timeslot_div;
	if ((timeslot_div = $j("#"+prefs_ts_div)).length == 0)
	    {
		// Create the div
		timeslot_div = $j("<div id='" + prefs_ts_div + "'></div>");
		container_div.append(timeslot_div);
		// Create the title
		timeslot_div.append("<h3>" + timeslot_data.label + "</h3><br/>");
	    }

	// Check if the interested div doesn't exist yet, and set interested_div at
	// the same time
	var interested_div;
	if ((interested_div = $j("#"+prefs_ts_div_by_priority(false))).length == 0)
	    {
		// Create the div
		interested_div = $j("<p id='" + prefs_ts_div_by_priority(false) + "'></p>");
		// Give it a title
		timeslot_div.append("<p><u>Interested classes:</u></p>");
		timeslot_div.append(interested_div);
	    }
	
	// Check if the priority div doesn't exist yet, and set priority_div at the
	// same time
	var priority_div;
	if ((priority_div = $j("#"+prefs_ts_div_by_priority(true))).length == 0)
	    {
		// Create the div
		priority_div = $j("<p id='" + prefs_ts_div_by_priority(true) + "'></p>");
		// Give it a title
		timeslot_div.append("<p><u>Priority flagged classes:</u></p>");
		timeslot_div.append(priority_div);
	    }

	// Make a local reference to the sections for readability
	data_starting_sections = timeslot_data['starting_sections'];
	priority_sections = [];
	interested_sections = [];
	for(i in data_starting_sections)
	    {
		if(sections[data_starting_sections[i]].lottery_priority)
		    {
			priority_sections.push(data_starting_sections[i]);
		    }
		if(sections[data_starting_sections[i]].lottery_interested)
		    {
			interested_sections.push(data_starting_sections[i]);
		    }
	    }

	// Render all the priority classes
	if (priority_sections.length > 0)
	    {
		priority_div.html('');
		for (i in priority_sections)
		    {
			render_class_section(timeslot_data, priority_div, priority_sections[i]);
		    }
	    }
	else
	    {
		// Write "(None)" if there are no classes
		priority_div.html("<i><font color='red'>(None)<br/></font></i>");
	    }
	priority_div.append("<br/><br/>");

	// Render all the interested classes
	if (interested_sections.length > 0)
	    {
		interested_div.html('');
		for (j in interested_sections)
		    {
			render_class_section(timeslot_data, interested_div, interested_sections[j]);
		    }
	    }
	else
	    {
		// Write "(None)" if there are no classes
		interested_div.html("<i><font color='red'>(None)<br/></font></i>");
	    }
	interested_div.append("<br/>");
    
    }
};

 
function get_submit_data(){
    var building_submit_data = {};
    for(id in sections){
	s = sections[id];
	building_submit_data[id] = s['lottery_interested'];
	building_submit_data['flag_'+id] = s['lottery_priority']; 
    }
    return building_submit_data;
};
