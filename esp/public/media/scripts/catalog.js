dojo.require("dojox.dtl");
dojo.require("dojox.dtl.Context");
dojo.require("dojo.date");
dojo.require("dojo.date.stamp");
dojo.require("dojox.date.posix");

dojo.registerModulePath("Markdown", "/media/scripts/dojo-custom-modules/Markdown/");
dojox.dtl.register.filters("Markdown", "Markdown", ["markdown"]);

var ADJACENT_EVENT_SPREAD = 15; // Number of minutes between the end of one event 
                                // and the start of the next, less than which the
                                // two events will be seen as "adjacent".

var source_catalog = null;

var global_catalog = null;
var global_categories = null;

var categories_template = null;
var one_class_template = null;

function collect_meeting_times(times_list) {
    if (times_list.length == 0) {
	return times_list;
    }

    var collect_buffer = [];
    var collect_event = times_list[0];
    
    for (var i = 1; i < times_list.length; i++) {
	if (dojo.date.difference(times_list[i].start, collect_event.end, "minute") < ADJACENT_EVENT_SPREAD) {
	    collect_event.end = times_list[i].end;
	} else {
	    collect_buffer.push(collect_event);
	    collect_event = times_list[i];
	}
    }

    collect_buffer.push(collect_event);
    return collect_buffer;
}

function pretty_meeting_time(time) {
    return dojox.date.posix.strftime(time.start, "%a") + " " 
	+ dojox.date.posix.strftime(time.start, "%I:%M%p").toLowerCase() 
	+ "--" + dojox.date.posix.strftime(time.end, "%I:%M%p").toLowerCase();
}

function save_catalog(catalog, ioArgs) {
    source_catalog = catalog;
    setTimeout(process_saved_catalog, 0);
}

function process_saved_catalog() {
    // Initialize the global_categories global variable
    global_categories = [];

    var catalog = dojo.fromJson(source_catalog);    
    var last = '';
    var all_full;
    var timerange_collector;

    for (var c = 0; c < catalog.length; c++) {
	all_full = true;
	for (var d = 0; d < catalog[c].get_sections.length; d++) {
	    if (catalog[c].get_sections[d].num_students >= catalog[c].class_size_max) {
		catalog[c].get_sections[d].isFull = true;
	    } else {
		catalog[c].get_sections[d].isFull = false;
		all_full = false;
	    }

	    timerange_collector = [];
	    for (var e = 0; e < catalog[c].get_sections[d].get_meeting_times.length; e++) {
		catalog[c].get_sections[d].get_meeting_times[e].start = dojo.date.stamp.fromISOString(catalog[c].get_sections[d].get_meeting_times[e].start);
		catalog[c].get_sections[d].get_meeting_times[e].end = dojo.date.stamp.fromISOString(catalog[c].get_sections[d].get_meeting_times[e].end);

		timerange_collector.push(catalog[c].get_sections[d].get_meeting_times[e]);
	    }

	    catalog[c].get_sections[d].collected_meeting_times = collect_meeting_times(timerange_collector);

	    timerange_collector = []
	    for (var e = 0; e < catalog[c].get_sections[d].collected_meeting_times.length; e++) {
		timerange_collector.push( pretty_meeting_time(catalog[c].get_sections[d].collected_meeting_times[e]) );
	    }
	    catalog[c].get_sections[d].pretty_meeting_times = timerange_collector.join(", ");
	}

	catalog[c].isFull = all_full;
	
	if ( catalog[c].category.category != last ) {
	    global_categories.push(catalog[c].category);
	    last = catalog[c].category.category;
	}

	if ( user_grade != null && (user_grade < catalog[c].grade_min || user_grade > catalog[c].grade_max) ) {
	    catalog[c].not_in_grade_range = true;
	} else {
	    catalog[c].not_in_grade_range = false;
	}

	catalog[c].class_is_available = ( !catalog[c].not_in_grade_range && !catalog[c].isFull );
    }
    
    global_catalog = catalog;
    
    setTimeout(one_time_render_catalog, 0);
}

function save_categories_template(template, ioArgs) {
    categories_template = template;
    setTimeout(one_time_render_catalog, 0);
}

function save_class_template(template, ioArgs) {
    one_class_template = template;
    setTimeout(one_time_render_catalog, 0);
}

var _one_time_render_catalog = false;
function one_time_render_catalog() {
    // Don't actually render if we don't have all of our data yet!
    if ( global_catalog == null || global_categories == null ||
	 categories_template == null || one_class_template == null ) {
	return;
    }
    
    if (!_one_time_render_catalog) {
	_one_time_render_catalog = true;
	render_catalog();
    }
}

function render_catalog() {
    // Render the Categories panel
    var category_template = new dojox.dtl.Template(categories_template);
    var category_context = new dojox.dtl.Context({ categories: global_categories });
    document.getElementById("categories").innerHTML = category_template.render(category_context);
    
    var class_template = new dojox.dtl.Template(one_class_template);
    var output_classes = [];
    var class_context;
    for (var c = 0; c < global_catalog.length; c++) {
	class_context = new dojox.dtl.Context({ cls: global_catalog[c] });
	rendered_text = class_template.render(class_context);
	output_classes.push( rendered_text );
    }
    
    document.getElementById("classes").innerHTML = output_classes.join("<br />");
}

function get_catalog_data() {
    dojo.xhrGet({
	    url: "catalog_json",
	        handleAs: "text",
	        load: save_catalog
		});
    dojo.xhrGet({
	    url: "/media/templates/program/modules/studentclassregmodule/categories.html",
	        handleAs: "text",
	        load: save_categories_template
		});
    dojo.xhrGet({
	    url: "/media/templates/program/modules/studentclassregmodule/class.html",
	        handleAs: "text",
	        load: save_class_template
		});
}
