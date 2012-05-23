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
    // Create the dialog used to show class info
    create_class_info_dialog();

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


function Timeslot(data){
    var timeslot_data = data;
    var timeslot_id = data['id'];

    //some div ids
    var ts_div = "TS_"+data["id"];
    var ts_table_div = "TS_TABLE_" + data["id"];
    var ts_carryover_div = "TS_C_" + data["id"];
    var ts_walkin_div = "TS_W_" + data["id"];
    var ts_radio_name = data["label"] + "_priority";
    var ts_no_preference_id = data["label"] + "_no_preference";

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
	carryover_id_list = timeslot_data['sections'];
	class_id_list = timeslot_data['starting_sections'];
	user_grade = esp_user['cur_grade'];

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
	//$j("#"+ts_no_preference_id(timeslot['label'])).prop("checked", true);

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
	    if(user_grade >= section['grade_min'] && user_grade <= section['grade_max'] || esp_user['cur_admin'] == 1){
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
		$j("#"+ts_carryover_div).append(this.get_carryover_html(carryovers_list[i], timeslot_id));
	    }
	}
    };

    this.get_walkin_html = function(class_data, timeslot_id){
	// Create a walkin div using a template with keywords replaced below
	template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE% [<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]</p>"
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title'])
	.replace(/%CLASS_LENGTH%/g, Math.round(class_data['length']))
        .replace(/%CLASS_ID%/g, class_data['id']);
	return template;
    };

    this.get_carryover_html = function(class_data, timeslot_id){
	// Create a carried-over class div using a template with keywords replaced below
	template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE% [<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]</p>"
	.replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
	.replace(/%CLASS_TITLE%/g, class_data['title'])
	.replace(/%CLASS_LENGTH%/g, Math.round(class_data['length']))
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
    }
}
 
// The class description popup is a global variable, because we only want
// one object, and we don't want to recreate it each time
var class_desc_popup;
// Function to initially create the class description popup (using jQuery UI dialogs)
create_class_info_dialog = function(){
    class_desc_popup = $j('<div></div>').dialog({
	    autoOpen: false,
	    minWidth: 400,
	    minHeight: 300,
	    modal: true,
	    buttons: {
		Ok: function() {
		    $j(this).dialog("close");
		}
	    },
	    title: ''
	});
};

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
	ts = new Timeslot(sorted_timeslots[index])
	$j("#timeslots_anchor").before(ts.get_timeslot_html());
	ts.add_classes_to_timeslot(sections);//needs to be updated w/ object-orientedness
    }

    //recreate the accordion now to update for the timeslots
    $j("#lsr_content").accordion('destroy').accordion(accordion_settings);
};

// Dictionary to keep track of classes' extra info as and when we load them
var class_info = {};
// Initial popup that tells the user we're loading the class data
loading_class_desc = function(){
    class_desc_popup.dialog('option', 'title', 'Loading');
    class_desc_popup.dialog('option', 'width', 400);
    class_desc_popup.dialog('option', 'height', 200);
    class_desc_popup.dialog('option', 'position', 'center');
    class_desc_popup.html('Loading class info...');
    class_desc_popup.dialog('open');
};


// Function to fill the class description popup
fill_class_desc = function(class_id){
    var parent_class_id = sections[class_id].parent_class;
    extra_info = class_info[parent_class_id];
    class_desc_popup.dialog('option', 'title', sections[class_id].emailcode + ": " + extra_info.title);
    class_desc_popup.dialog('option', 'width', 600);
    class_desc_popup.dialog('option', 'height', 400);
    class_desc_popup.dialog('option', 'position', 'center');
    class_desc_popup.html('');
    class_desc_popup.append("<p><b>Category:</b> " + extra_info.category + "</p>");
    //class_desc_popup.append("<p>Difficulty: " + extra_info.difficulty + "</p>");
    class_desc_popup.append("<p><b>Description:</b> " + extra_info.class_info + "</p>");
};


// Called to open a class description
open_class_desc = function(class_id){
    // Display a loading popup while we wait
    loading_class_desc();

    // Get the class info if we don't have it already
    var parent_class_id = sections[class_id].parent_class;
    if (!class_info[parent_class_id]){
	json_get('class_info', {'class_id': parent_class_id}, function(data){
	    // Once we get the class data, store it for later, then go
	    // fill the popup
	    class_info[parent_class_id] = data.classes[parent_class_id];
	    fill_class_desc(class_id);
	});
    }
    else{
	// If we already have the data, go fill the popup
	fill_class_desc(class_id);
    }
};
