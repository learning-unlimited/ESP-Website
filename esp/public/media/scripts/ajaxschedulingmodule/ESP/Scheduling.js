var load = function() {
    json_data = {}
    var data = {}
    json_components = ['timeslots', 'schedule_assignments', 'rooms', 'sections', 'lunch_timeslots', 'resource_types'];
    json_fetch(json_components, function(d) {
	debug_log(d)
	for (var i in d) {
	    // Deal with prototype failing
	    if (typeof d[i] === 'function') { continue; }
	    data[i] = d[i];
	}
	
	ESP.Scheduling.init(data);
    }, json_data);
};

/*
 * the main application class
 */
ESP.Scheduling = function(){
    function init(test_data_set){
        $j('#body').hide()

        // ensure event manager is empty before we begin setting up
        ESP.Utilities.evm.unbind();

	//Add debug features
	if (debug_on && !ESP.Scheduling.hasOwnProperty('debug_features_added')){
	    $j('#body').append(
		$j("<input/>")
		    .attr({type: "button", value: "Fetch Updates", id: "fetch_updates"})
		    .click(ESP.Scheduling.fetch_updates)
	    );

	    //for testing log clearing behavior
	    $j('#body').append(
		$j("<input/>")
		    .attr({type: "button", value: "Clear update log", id: "clear_log"})
		    .click(function(e) {
			req = { csrfmiddlewaretoken: csrf_token() }

			$j.post('ajax_clear_change_log', req).success(function(data, status){
			    console.log("log cleared");
			})
		    })
	    );

	    ESP.Scheduling['debug_features_added'] = true;
	}
    
        ESP.Scheduling.classes_by_time_type = null;
        ESP.Scheduling.ms_classes_by_time = null;

        this.directory = new ESP.Scheduling.Widgets.Directory([]);
        this.searchbox = new ESP.Scheduling.Widgets.SearchBox(this.directory);

        var pd = this.data = process_data(test_data_set);
        this.raw_data = test_data_set;
        if (!this.status) {
            this._status = new ESP.Scheduling.Widgets.StatusBar('#statusbar');
            this.status = this._status.setStatus.bind(this._status);
            this.status('success','Welcome to the scheduling app!');
        }

        this.matrix = new ESP.Scheduling.Widgets.Matrix(pd.times, pd.rooms, pd.blocks)
        this.roomfilter = new ESP.Scheduling.Widgets.RoomFilter(this.matrix);
        this.garbage   = new ESP.Scheduling.Widgets.GarbageBin();

	//TODO:  add directory contents

        ESP.Utilities.evm.bind('drag_dropped', function(event, data){
            var extra = {
                blocks:data.blocks, section:data.section
            };
            //in the past, we've done block_section_assignment_request firing immediately after block_section_unassignment_request here
            //now we let Matrix.js call block_section_assignment_request with the 'recurse' data after the unassignment HTTP request completes
            ESP.Utilities.evm.fire('block_section_unassignment_request',{ section: data.section, blocks: data.section.blocks || [], recurse: extra });
            if(data.section.blocks !== undefined && data.section.blocks[0] !== undefined && extra.blocks[0] !== undefined) {
            	console.log("Rescheduling [" + data.section.text + "] from " + data.section.blocks[0].time.text + " in " + data.section.blocks[0].room.text + " to " + extra.blocks[0].time.text + " in " + extra.blocks[0].room.text);
            } else if(extra.blocks[0] !== undefined) {
            	console.log("Rescheduling [" + data.section.text + "] to " + extra.blocks[0].time.text + " in " + extra.blocks[0].room.text);
            }
        });
        ESP.Utilities.evm.bind('block_section_assignment_request', function(event, data){
            ESP.Utilities.evm.fire('block_section_assignment',data);
        });
        ESP.Utilities.evm.bind('block_section_unassignment_request', function(event, data){
            ESP.Utilities.evm.fire('block_section_unassignment',data);
        });

        apply_existing_classes(this.data.schedule_assignments, this.data)
        this.directory.filter();
    
        // make sure to refresh when sections get scheduled/unscheduled
        // it's here at the end to avoid needless work while the matrix is being set up
        var dir = this.directory;
        ESP.Utilities.evm.bind('block_section_assignment_success', function(event, data){
            dir.filter();
        });
	window_height = window.innerHeight - $j('#statusbar-wrapper').height() - 60;
        $j('#body').show()
	
	//size some things
	$j('.directory-table-wrapper').css("max-width", window.innerWidth - 50);
	$j('.directory-table-wrapper').css("min-width", 50);

	$j('#directory-accordion').height(window_height);
	$j("#directory-target").css("max-width", window.innerWidth-$j('.matrix').width() - 60);
	$j("#directory-target").css("min-width", 50);
	$j('#directory-accordion').accordion({fillSpace: "true"});

	//make matrixx resizeable
	$j('.matrix').resizable({handles: "e"})
	$j('.matrix').css("max-width", window.innerWidth - 50);
	$j('.matrix').css("min-width", 50);
	$j('.matrix').height(window_height);
	$j('.matrix-body').height($j('.matrix').height()-$j('.matrix-column-header-box').height()-2);

        //make matrix header fixed to the top
        $j('.matrix').scroll(function (event) {
            $j('.matrix-header').css('top', $j('.matrix').scrollTop());
            $j('.matrix-row-header-box').css('left', $j('.matrix').scrollLeft());
            $j('td.matrix-corner-box').css('left', $j('.matrix').scrollLeft());
        });

	//set last_fetched_index to the initial age
	if(!ESP.Scheduling.hasOwnProperty('last_fetched_index')) {
	ESP.Scheduling.last_fetched_index = 0
	}

	//TODO:  add verbose mode here
        //console.log("Classes of each type in each timeblock:");
        for (var time in ESP.Scheduling.classes_by_time_type) {
            for (var type in ESP.Scheduling.classes_by_time_type[time]) {
                //console.log("-- " + time + ",\t" + type + ":\t" + ESP.Scheduling.classes_by_time_type[time][type]);
            }
        }
    
        //console.log("Middle-School Classes of each type in each timeblock:");
        for (var time in ESP.Scheduling.ms_classes_by_time) {
            //console.log("-- " + time + ":\t" + ESP.Scheduling.ms_classes_by_time[time]);
        }
    };
    
    // process data
    function process_data(data){
        var processed_data = {
            times: [],
            rooms: [],
            blocks: [],
            sections: [],
            block_index: {},
            teachers: [],
            schedule_assignments: [],
            resource_types: []
        };

        processed_data.schedule_assignments = data.schedule_assignments;

        var Resources = ESP.Scheduling.Resources;

        // resourcetypes
        for (var i in data.resource_types) {
	    // Handle prototype adding random stuff
	    if (typeof data.resource_types[i] === 'function') continue;

            var rt = data.resource_types[i];
            Resources.create('RoomResource', { uid: rt.uid, text: rt.name, description: rt.description, attributes: rt.attributes });
        }

        // times
        for (var i in data.timeslots) {
	    // Handle prototype being unhappy
	    if (typeof data.timeslots[i] === 'function') {continue;}
            var t = data.timeslots[i];
            // constructors for native classes can't be called via apply()... :-(
            var start = new Date(t.start[0],t.start[1],t.start[2],t.start[3],t.start[4],t.start[5]).getTime();
            var end = new Date(t.end[0],t.end[1],t.end[2],t.end[3],t.end[4],t.end[5]).getTime();
            var r;
            processed_data.times.push(r =
                    Resources.create('Time',
				     { uid: t.id, text: t.short_description, start: start, end: end, length: end - start + 15*60000, is_lunch: t.is_lunch?t.is_lunch:false }));
        }
        processed_data.times.sort(function(x,y){
            return x.start - y.start;
        });
        for (var i = 0; i < processed_data.times.length - 1; i++) {
            var t = processed_data.times[i];
            var t2 = processed_data.times[i+1];
            t.seq = Resources.Time.sequential(t,t2) ? t2 : null;
            // console.log("Are " + t.text + " and " + t2.text + " sequential? " + t.seq);
        }

        // rooms / blocks
        var BlockStatus = Resources.BlockStatus;
        for (var i in data.rooms) {
	    // Deal with prototype putting random functions in everything
	    if (typeof data.rooms[i] === 'function') { continue; }

            var r = data.rooms[i];
            var assd_resources =  r.associated_resources.map(function(x){
                var res = Resources.get('RoomResource',x);
                return (res ? res.text : "");
            });
            var room = Resources.create('Room',{
                uid: r.uid,
                text: r.text,
                block_contents: ESP.Utilities.genPopup("r-" + r.uid, r.text, {
                    'Size:': r.num_students.toString(),
                    'Resources:': assd_resources
                }, null, false),
                resources: assd_resources,
                size: r.num_students
            });
            processed_data.rooms.push(room);
            var rid = room.uid;
            processed_data.block_index[rid] = {};
            for (var j = 0; j < r.availability.length; j++) {
                var t = Resources.get('Time', r.availability[j]);
                var block;
                processed_data.blocks.push(block = Resources.create('Block', { 
                                            time: t,
                                            room: r,
                                            processed_room: room,
                                            status:BlockStatus.AVAILABLE,
                                            uid: [t.uid,r.uid]}));
                processed_data.block_index[rid][block.time.uid] = block;
            }
        }

        for (var i = 0; i < processed_data.blocks.length; i++) {
            var b = processed_data.blocks[i];
            b.seq = b.time.seq ? processed_data.block_index[b.room.uid][b.time.seq.uid] : null;
            // console.log("Block " + b.time + "/" + b.room + " seq is " + b.time.seq);
        }
        processed_data.rooms.sort(function(x,y){
            return x.uid < y.uid ? -1 : x.uid == y.uid ? 0 : 1;
        });
    
        // teachers
        for (var i in data.teachers) {
	    // Deal with prototype adding stuff to objects
	    if (typeof data.teachers[i] === 'function') continue;

            var t = data.teachers[i];
            processed_data.teachers.push(Resources.create('Teacher',{
		id: t.id,
                text: t.first_name + " " + t.last_name,
                block_contents: ESP.Utilities.genPopup(t.id, t.first_name + " " + t.last_name, {'Available Times:':
                    t.availability.map(function(x){
                        var res = Resources.get('Time',x);
                        return res ? res.text : "N/A";
                    }) }, null, false),
                available_times: t.availability.map(function(x){return Resources.get('Time',x);}),
                sections: t.sections
            }));
        }
    
        // sections
        for (var i in data.sections) {
	    // Deal with prototype
	    if (typeof data.sections[i] === 'function') { continue; }

	    // Causes scoping correctly... there's probably a better way to do this
	    (function() {
		var c = data.sections[i];
		var s;
	
		// Function to handle hovering over a section -- we need to trigger the dynamic
		// loading of extra data needed for the popup
		var onHoverHandler = function(node) {
		    // Determine which JSON views need to be loaded
		    var json_list = [];
		    if (!s.class_info) {
			json_list.push('class_info');
		    }
		    if (!s.class_size_info) {
			json_list.push('class_size_info');
		    }
		    if (!s.class_admin_info) {
			json_list.push('class_admin_info');
		    }

		    // Function to actually populate the class popup with the new data
		    var populate_class_popup = function(called_node) {
			// Create the size and popup data
			var size_info = [
			    s.class_size_max ? " max size=" + s.class_size_max.toString() : "",
			    s.max_class_capacity ? " max cap=" + s.max_class_capacity.toString() : "",
			    s.optimal_class_size ? " optimal size=" + s.optimal_class_size.toString() : "",
			    s.optimal_class_size_range ? " optimal size range=" + s.optimal_class_size_range : ""
			];
			var popup_data = {
			    'Title:': s.text,
			    'Teachers': s.teachers.map(function(x){ return x.text; }),
			    'Requests:': s.resource_requests ? 
				s.resource_requests.map(function(x){
				    var res = x[0];
				    var text = x[1] || "(none)";
				    return (res ? (res.text + ": " + text) : null);
				}) : "(none)",
			    'Size:': size_info.filter(function (x) {return (x.length > 0);}).join(", "),
			    'Grades:': s.grade_min ? (s.grade_min + "-" + s.grade_max) : "(n/a)",
			    "Prereq's:": s.prereqs,
			    'Comments:': s.comments
			};
			if (s.allowable_class_size_ranges.size() > 0)
			    popup_data['Allowable Class-Size Ranges:'] = c.allowable_class_size_ranges;
			ESP.Utilities.fillPopup("s-" + s.id, s.block_contents, popup_data, false);
		    };
		    
		    if (json_list.length > 0) {
			node.children('.tooltip_popup').html("Loading...");
			var json_left = json_list.length;

			for (var i in json_list) {
			    // Deal with prototype
			    if (typeof json_list[i] === 'function') { continue; }

			    // Handle scoping issues; once again, probably a better way to do this
			    (function() {
				var json_component = json_list[i];
				json_get(json_component, {'section_id': s.id}, function(data) {
				    if (json_component == 'class_info') {
					s.class_info = true;
					s_data = data.sections[s.id];
					s.prereqs = s_data.prereqs;
				    }
				    else if (json_component == 'class_size_info') {
					s.class_size_info = true;
					s_data = data.sections[s.id];
					s.class_size_max = s_data.class_size_max;
					s.optimal_class_size = s_data.optimal_class_size;
					s.optimal_class_size_range = s_data.optimal_class_size_ranges;
					s.allowable_class_size_ranges = s_data.allowable_class_size_ranges;
					s.max_class_capacity = s_data.max_class_capacity;
				    }
				    else if (json_component == 'class_admin_info') {
					s.class_admin_info = true;
					s_data = data.sections[s.id];
					if (s_data.resource_requests[s.id]) {
					    s.resource_requests = s_data.resource_requests[s.id].map(function(x){ return [Resources.get('RoomResource', x[0]), x[1]]; });
					}
					else {
					    s.resource_requests = null;
					}
					s.comments = s_data.comments;
				    }
				    
				    // If we've processed everything...
				    if(--json_left == 0) {
					populate_class_popup(node);
				    }
				});
			    })();
			}
		    }
		};

		// Finally, create our Resource with what we have now
		processed_data.sections.push(s = Resources.create('Section',{
            uid: c.id,
            class_id: c.parent_class,
            code: c.emailcode,
            class_info: false,
            class_size_info: false,
            class_admin_info: false,
	    class_size_max: c.class_size_max,
            block_contents: ESP.Utilities.genPopup("s-" + c.id, c.emailcode, {}, onHoverHandler, null, false),
            category: c.category,
            length: Math.round(c.length*10)*3600000/10 + 600000, // convert hr to ms
            length_hr: Math.round(c.length * 2) / 2,
            id: c.id,
            teachers: c.teachers.map(function(x) {
                return Resources.get('Teacher', x);
            }),
            text: c.title,
            status: c.status,
            grade_min: c.grade_min,
            grade_max: c.grade_max
		}));

					     
		// console.log("Added section: " + s.code + " (time " + s.length + " = " + s.length_hr + " hr "); 

		// Make sure the Directory now knows this section exists
		ESP.Scheduling.directory.addEntry(s, false);
            })();
	}
	ESP.Scheduling.directory.filter();

	//Finish teachers -- map the sections now that they exist
	for (var i in processed_data.teachers) {
	    // Deal with prototype
	    if (typeof processed_data.teachers[i] === 'function') continue;

	    processed_data.teachers[i].sections = processed_data.teachers[i].sections.map(function(x) {
		return Resources.get('Section', x);
	    });
	}

        return processed_data;
    };
   
    var fetch_updates = function()  {
	$j.getJSON('ajax_change_log', {'last_fetched_index': ESP.Scheduling.last_fetched_index}, function(d, status) {
	    //if we need to reload
	    if (d['other'] && d['other'][0]['command'] == "reload"){
		    console.log("reloading")
		    load()
		}
	    else{
		apply_existing_classes(d.changelog, this.data)
		//update last change time with received indices
		for(var i = 0; i < d.changelog.length; i++){
			if(d.changelog[i].index > ESP.Scheduling.last_fetched_index) {
		    	ESP.Scheduling.last_fetched_index = d.changelog[i].index
		    }
		}
	    }
	});
    };

    var apply_existing_classes = function(assignments, data) {
        var Resources = ESP.Scheduling.Resources;
        var rsrc_sec = {}
        var sa;

        for (var i in assignments) {
	    // Handles prototype being angry
	    if (typeof assignments[i] === 'function') {continue;}

            sa = assignments[i];
	    debug_log (sa);

	    //create a list or erase previous assignment
            rsrc_sec[sa.id] = [];
	    for (var j = 0; j < sa.timeslots.length; j++)
	    {
	    resource = Resources.get('Block', [sa.timeslots[j],sa.room_name]);
	    if(resource !== undefined) {
			rsrc_sec[sa.id].push(resource);
		}
	    }
        }

        var Section;
        var sec_id;
        for (var i = 0; i < ESP.Scheduling.data.sections.length; i++) {
            sec_id = ESP.Scheduling.data.sections[i].uid;

            if (rsrc_sec[sec_id]) {
		//unschedule
		ESP.Utilities.evm.fire('block_section_unassignment_request', { 
		    section: Resources.get('Section', sec_id),
		    blocks: [],
		    nowriteback: true /* Don't tell the server about this assignment */
		});
		//reschedule if we have no blocks
		if (rsrc_sec[sec_id].length > 0){ 
		    ESP.Utilities.evm.fire('block_section_assignment_request', { 
			section: Resources.get('Section', sec_id), 
			blocks: rsrc_sec[sec_id],
			nowriteback: true /* Don't tell the server about this assignment */
		    });
		}
            }
        }

	//update directory (sometimes this happens correctly without this call, and sometimes it doesn't
	ESP.Scheduling.directory.filter()
    }

    var validate_block_assignment = function(block, section, str_err) {
        // check status
        if (block.status != ESP.Scheduling.Resources.BlockStatus.AVAILABLE) {
            //console.log("Room " + block.room + " at " + block.time + " is not available"); 
            return false;
        }

        var time = block.time;	

        for (var i = 0; i < section.teachers.length; i++) {
            var valid = false;
            var teacher = section.teachers[i];
            for (var j = 0; j < teacher.available_times.length; j++) {
                if (teacher.available_times[j] == time) {
                    valid = true;
                    break;
                }
            }
            if (!valid)
            {
		//console.log("Teacher '" + section.teachers[i].text + "' not available at time '" + time.text + "'");
		return (str_err ? "Teacher '" + section.teachers[i].text + "' not available at time '" + time.text + "'" : false);
            }
        }

        // check for class over- or under-size
        var room_size = block.room.num_students;
        var class_size = (section.max_class_capacity ? section.max_class_capacity : section.optimal_class_size);
        if (class_size && (class_size > room_size * 1.5 || class_size < room_size * 0.666)) {
            // This shouldn't be an actual error; sometimes it'll be the "right" thing to do
            //return (str_err ? "Class '" + section.text + "' (size: " + class_size + " students) not the right size for room '" + block.room.text + "' (max size: " + room_size + " students)" : false);
            //console.log("Warning:  Class '" + section.text + "' (size: " + class_size + " students) not the right size for room '" + block.room.text + "' (max size: " + room_size + " students)");
        }

        // check for teacher class conflicts
        // also check for making this class's teachers run all over campus (horrible dirty hack)
        var class_bldg = block.room.text.split('-');
        if (class_bldg.length > 1 && class_bldg[0].length < 4) {
            class_bldg = class_bldg[0];
        } else {
            class_bldg = null;
        }
        for (var i = 0; i < section.teachers.length; i++) {
            var teacher = section.teachers[i];
            for (var j = 0; j < teacher.sections.length; j++) {
                var other_section = teacher.sections[j];
                if (other_section == section) continue;
                for (var k = 0; k < other_section.blocks.length; k++) {
                    var other_block = other_section.blocks[k];
                    if (other_block.time == time) {
                        console.log("Teacher '" + teacher.text + "' cannot teach classes '" + section.code + "' and '" + other_section.code + "' simultaneously ('" + time.text + "')");
                        return (str_err ? ("Teacher '" + teacher.text + "' cannot teach classes '" + section.code + "' and '" + other_section.code + "' simultaneously ('" + time.text + "')") : false);
                    }
                    if (other_block.seq == block || block.seq == other_block) {
                        var other_class_bldg = other_block.room.text.split('-');
                        if (other_class_bldg.length > 1 && other_class_bldg[0].length < 4) {
                            other_class_bldg = other_class_bldg[0];
                            if (other_class_bldg != class_bldg) {
                                console.log("Teacher '" + teacher.text + "' running between bldg " + class_bldg + " (" + block.time.text + ") and bldg " + other_class_bldg + " (" + other_block.time.text + ")");
                                return (str_err ? ("Teacher '" + teacher.text + "' running between bldg " + class_bldg + " (" + block.time.text + ") and bldg " + other_class_bldg + " (" + other_block.time.text + ")") : false);
                            }
                        }
                    }
                }
            }
        }
    
        // resources
        // WARNING:  This is sketchy!; the website does not currently store/provide enough information
        // about the resources associated with a block, to actually do this test.
        // But try anyway.
        var found_resource = true;
        if (block.resources) {
            for (var i = 0; i < block.resources.length; i++) {
                found_resource = false;
                for (var j = 0; j < section.resource_requests.length; j++) {
                    if (block.resources[i] == section.resource_requests[j].text) {
                        found_resource = true;
                        break;
                    }
                }
                if (!found_resource) {
                    break;
                }
            }
            if (!found_resource) {
                //console.log("Class '" + section.text + "' requested a resource ('" + section.resource_requests[j].text + "') not available in room '" + block.room.text + "' (note that the website's resource tracker is not fully functional at this time!)");
                return (str_err ? "Class '" + section.text + "' requested a resource ('" + section.resource_requests[j].text + "') not available in room '" + block.room.text + "' (note that the website's resource tracker is not fully functional at this time!)" : true);
            }
        }
    
        // Accumulate classes of each type, as scheduled so far
        if (!ESP.Scheduling.classes_by_time_type) {
            ESP.Scheduling.classes_by_time_type = {};
        }
        if (!ESP.Scheduling.classes_by_time_type[block.time.text]) {
            ESP.Scheduling.classes_by_time_type[block.time.text] = {};
        }
        if (!ESP.Scheduling.classes_by_time_type[block.time.text][section.category]) {
            ESP.Scheduling.classes_by_time_type[block.time.text][section.category] = 1;
        } else {
            ESP.Scheduling.classes_by_time_type[block.time.text][section.category] ++;
        }
    
        if (section.grade_min < 9) {
            if (!ESP.Scheduling.ms_classes_by_time) {
                ESP.Scheduling.ms_classes_by_time = {};
            }
            if (!ESP.Scheduling.ms_classes_by_time[block.time.text]) {
                ESP.Scheduling.ms_classes_by_time[block.time.text] = 1;
            } else {
                ESP.Scheduling.ms_classes_by_time[block.time.text] ++;
            }      
        }
    
        return (str_err ? "OK" : true);
    };
    
    var validate_start_time = function(time, section, str_err) {
        var length = Math.ceil(section.length_hr);
        if (!length || length == 0)
        {
            return (str_err ? "No length defined!" : false)
        }

        //  Check for not scheduling across a contiguous group of lunch periods - check start block only
        var test_time = time;
        var covered_lunch_start = false;

        // Start with the proposed start time and iterate over all time blocks the section will need
        var time_included = 0;
        for (var i = 0; i < length; i++)
        {
            //  Maintain a count of the time included by the timeslots so far.
            time_included += test_time.length;

            if (test_time.is_lunch && !covered_lunch_start)
            {
                //  Check that this is the first lunch in the group:
                //  - this is the first time slot, or
                //  - the previous time slot is not a lunch block
                if ((ESP.Scheduling.data.times.indexOf(test_time) == 0) || !(ESP.Scheduling.data.times[ESP.Scheduling.data.times.indexOf(test_time) - 1].is_lunch))
                {
                    covered_lunch_start = true;
                }
            }

            //  Check that the section would not run over the end of the program,
            //  or the end of the contiguous time block (if there is a break).
            //  (10 min error tolerance)
            //  This is a temporary workaround for a larger problem; see Github issue #972.
            //  - Michael P, 1/24/2014
            if (!test_time.seq)
            {
                if (section.length > time_included + 10 * 60 * 1000)
                    return (str_err ? "Section " + section.code + " does not fit within the contiguous time available" : false);
                else
                    return true;
            }

            //  But, if our class period overlapped with the beginning of the lunch sequence
            //  and now also overlaps with the end of the lunch sequence, that's a conflict.
            else if (covered_lunch_start && !(test_time.seq.is_lunch))
            {
                return (str_err ? "Section " + section.code + " starting at " + time.text + " would conflict with a group of lunch periods" : false);
            }

        //  Move on to the next time slot.
        test_time = test_time.seq;
        }

        return (str_err ? "OK" : true);
    };
    
    var self = {
        init: init,
        validate_block_assignment: validate_block_assignment,
        validate_start_time: validate_start_time,
	fetch_updates: fetch_updates,
	//data: data
    };

    return self;
}();


/*
 * initialize the page
 */
$j(function(){
    ESP.version_uuid = null;

    $j.getJSON('ajax_schedule_last_changed', function(d, status) {
        if (status == "success") {
            ESP.version_uuid = d['val'];
            ESP.Scheduling.last_fetched_index = d['latest_index'];
        }
    });

    //json_fetch_data(json_components, json_data);
    load()

    //if we're in debug mode, we can use the button at the top to get updates
    if (!debug_on){
	setInterval(function() {
            $j.getJSON('ajax_schedule_last_changed', function(d, status) {
		if (status == "success") {
                    if (d['val'] != ESP.version_uuid) {
			ESP.version_uuid = d['val'];
			//location.reload(true);
			ESP.Scheduling.fetch_updates();
                    } else {
			ESP.Scheduling.last_fetched_index = d['latest_index'];
                    }
		} else {
                    ESP.Scheduling.status('error','Unable to refresh data from server.');
		}
            });
	}, 10000);

	setInterval(function() {
	    load()
	}, 600000);
    }
});
