
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

    user_grade = esp_user['cur_grade'] + (typeof increment_grade == 'undefined' ? 0 : increment_grade);

    json_fetch(data_components, show_app);
});


var accordion_settings;	

// Initializes various jQuery UI things
jquery_ui_init = function(){

    // Create the accordion settings
    accordion_settings = {
	// Class 'header' elements will be considered headers by the accordion
	header: ".header",
	heightStyle: "content",
	collapsible: true,
	beforeActivate: function(event, ui) {
	    // If we're switching to the preferences tab, update it
	    if (ui.newPanel.attr("id") == "preferences")
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

get_walkin_header_html = function()
{
    if (open_class_registration) {
        return "<h3>" + open_class_category.category + "</h3>\
        <div id='%TIMESLOT_WALKIN_DIV%' style='margin:1em 1em 1em 1em'></div>";
    }
    return "";
}

walkin_header_html = get_walkin_header_html();

get_timeslot_html = function(timeslot_data)
{
    // Create some html for the timeslot, making use of keywords which are
    // replaced by values below
    template = "\
    <h3 class='header'><a href='#'><b>%TIMESLOT_LABEL% </b></a></h3>\
    <div id='%TIMESLOT_DIV%'>\
    " + walkin_header_html + "\
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
    </div><br>";
    template = template.replace(/%TIMESLOT_ID%/g, timeslot_data['id']);
    template = template.replace(/%TIMESLOT_DIV%/g, ts_div_from_id(timeslot_data['id']));
    template = template.replace(/%TIMESLOT_TABLE%/g, ts_table_from_id(timeslot_data['id']));
    template = template.replace(/%TIMESLOT_WALKIN_DIV%/g, ts_walkin_div_from_id(timeslot_data['id']));
    template = template.replace(/%TIMESLOT_CARRYOVER_DIV%/g, ts_carryover_div_from_id(timeslot_data['id']));
    template = template.replace(/%TIMESLOT_LABEL%/g, timeslot_data['label']);
    return template;
};

add_classes_to_timeslot = function(timeslot, sections){
    carryover_id_list = t['sections'];
    class_id_list = t['starting_sections'];
    user_grade = esp_user['cur_grade'];

    //adds the "no priority" radio button and defaults it to checked (this will change if we load a different, previously specified preference)
    var no_priority_template = "\
    <tr>\
        <td><p>\
            <input type=radio name=\"%TS_RADIO_NAME%\" onChange='priority_changed(null, %TIMESLOT_ID%)' id=\"%TS_NO_PREFERENCE_ID%\" checked></input>\
        </p></td>\
\
        <td></td>\
        <td><p>I would not like to specify a priority class for this timeblock.</p></td>\
    </tr>";
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
	if (typeof(id) != "number") continue;
        section = sections[id];

	// check grade in range or admin
	if((user_grade >= section['grade_min'] && user_grade <= section['grade_max']) || esp_user['cur_admin'] == 1){
            if(!open_class_registration || section['category_id'] != open_class_category["id"]){
                if (section['status'] > 0)
                {
                    has_classes = true;
                    classes_list.push(section);
                }
            }
        }
    }

    for(i in carryover_id_list){
        id = carryover_id_list[i];
	if (typeof(id) != "number") continue;
        section = sections[id];

	//check grade in range or admin
	if(section['status'] > 0 && user_grade >= section['grade_min'] && user_grade <= section['grade_max'] || esp_user['cur_admin'] == 1){
            if(open_class_registration && section['category_id'] == open_class_category["id"]){
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
        $j("#"+ts_walkin_div_from_id(timeslot['id'])).append("<i><font color='red'>(No walk-ins)</font></i>");
    }
    else if (open_class_registration){
    // Add all the walkins classes
        for(i in walkins_list){
	    if (typeof(walkins_list[i]) == "function") continue;
            $j("#"+ts_walkin_div_from_id(timeslot['id'])).append(get_walkin_html(walkins_list[i], timeslot['id']));
        }
    }
    // Add classes (starting in this timeblock) section
    if(!has_classes){
    //hopefully nobody will ever see this either :)
        $j("#"+ts_div_from_id(timeslot['id'])).append("<i><font color='red'>(No classes)</font></i>");
    }
    else{
    // Adds all classes that start in this timeblock
        for(i in classes_list){
	    if (typeof(classes_list[i]) == "function") continue;
        $j("#"+ts_table_from_id(timeslot['id']) + "> tbody:last").append(get_class_checkbox_html(classes_list[i], timeslot['id']));
        load_old_preferences(classes_list[i]);
        }
    }
    // Add carried over classes section
    if(!has_carryovers){
        $j("#"+ts_carryover_div_from_id(timeslot['id'])).append("<i><font color='red'>(No carry-overs)</font></i>");
    }
    else{
    // Adds all classes that are carried over from the previous timeblock
        for(i in carryovers_list){
	    if (typeof(carryovers_list[i]) == "function") continue;
            $j("#"+ts_carryover_div_from_id(timeslot['id'])).append(get_carryover_html(carryovers_list[i], timeslot['id']));
        }
    }
};

get_class_checkbox_html = function(class_data, timeslot_id){
    // Create the class div using a template that has keywords replaced with values below
    template = "\
    <tr>\
        <td><p>\
            <input type='radio'\
                   onChange='priority_changed(%CLASS_ID%, %TIMESLOT_ID%)'\
                   id=\"%CLASS_RADIO_ID%\"\
                   name=\"%TS_RADIO_NAME%\">\
            </input>\
        </p></td>\
        <td><p>\
            <input type='checkbox'\
                   onChange='interested_changed(%CLASS_ID%)'\
                   name=%CLASS_CHECKBOX_ID%\
                   id=%CLASS_CHECKBOX_ID%>\
            </input>\
        </p></td>\
        <td><p>%CLASS_EMAILCODE%: %CLASS_TITLE% <i>(%CLASS_LENGTH% hours)</i> [<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]</p></td>\
    </tr>"
	.replace(/%TIMESLOT_ID%/g, timeslot_id)
        .replace(/%TS_RADIO_NAME%/g, ts_radio_name(timeslots[timeslot_id].label))
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title'])
	.replace(/%CLASS_LENGTH%/g, Math.round(class_data['length']))
        .replace(/%CLASS_ID%/g, class_data['id'])
        .replace(/%CLASS_CHECKBOX_ID%/g, class_checkbox_id(class_data['id']))
        .replace(/%CLASS_RADIO_ID%/g, class_radio_id(class_data['id']));
    return template;
};

get_walkin_html = function(class_data, timeslot_id){
    // Create a walkin div using a template with keywords replaced below
    template = "<p>%CLASS_EMAILCODE%: %CLASS_TITLE% <i>(%CLASS_LENGTH% hours)</i> [<a href='javascript:open_class_desc(%CLASS_ID%)'>More info</a>]</p>"
        .replace(/%CLASS_EMAILCODE%/g, class_data['emailcode'])
        .replace('%CLASS_TITLE%', class_data['title'])
	.replace(/%CLASS_LENGTH%/g, Math.round(class_data['length']))
        .replace(/%CLASS_ID%/g, class_data['id']);
    return template;
};

get_carryover_html = function(class_data, add_link){
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
	     headers: {'X-CSRFToken': $j.cookie("esp_csrftoken")}
     });
};

