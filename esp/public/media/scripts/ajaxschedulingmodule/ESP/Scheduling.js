/*
 * the main application class
 */
ESP.Scheduling = function(){
    function init(test_data_set){
	// ensure event manager is empty before we begin setting up
	ESP.Utilities.evm.unbind();
	
	var pd = this.data = process_data(test_data_set);
	this.raw_data = test_data_set;
	if (!this.status) {
	    this._status = new ESP.Scheduling.Widgets.StatusBar('#statusbar');
	    this.status = this._status.setStatus.bind(this._status);
	    this.status('success','Welcome to the scheduling app!');
	}
	this.matrix = new ESP.Scheduling.Widgets.Matrix(pd.times, pd.rooms, pd.blocks);
	$j('#matrix-target').text('');
	$j('#matrix-target').append((new Date()).getMilliseconds());
	$j('#matrix-target').append(this.matrix.el);
	this.directory = new ESP.Scheduling.Widgets.Directory(pd.sections);
	this.searchbox = new ESP.Scheduling.Widgets.SearchBox(this.directory);
	this.garbage   = new ESP.Scheduling.Widgets.GarbageBin();
	$j('#directory-target').text('');
	$j('#directory-target').append(this.searchbox.el);
	$j('#directory-target').append(this.garbage.el.addClass('float-right'));
	$j('#directory-target').append(this.directory.el);
	
	//ESP.Utilities.evm.bind('drag_started',function(data){alert('!!!');});
	ESP.Utilities.evm.bind('drag_dropped', function(event, data){
		var extra = {
		    blocks:data.blocks, section:data.section
		};
		ESP.Utilities.evm.fire('block_section_unassignment_request',{ section: data.section, blocks: data.section.blocks || [] });
		ESP.Utilities.evm.fire('block_section_assignment_request',extra);
	    });
	ESP.Utilities.evm.bind('block_section_assignment_request', function(event, data){
		//alert('[' + data.block.uid + '] : [' + data.section.uid + ']');

		for (var i = 0; i < data.blocks.length; i++) {
		    if (!ESP.Scheduling.validate_block_assignment(data.blocks[i], data.section)) {
			console.log("Error:  Conflict when adding block " + data.blocks[i].room.text + " (" + data.blocks[i].time.text + ") to section " + data.section.code);
		    }
		}

		data.section.blocks = data.blocks;
		for (var i = 0; i < data.blocks.length; i++) {
		    data.blocks[i].section = data.section;
		}
		ESP.Utilities.evm.fire('block_section_assignment',data);
	    });
	ESP.Utilities.evm.bind('block_section_unassignment_request', function(event, data){
		//alert('[' + data.block.uid + '] : [' + data.section.uid + ']');
		data.section.blocks = [];
		for (var i = 0; i < data.blocks.length; i++) {
		    data.blocks[i].section = null;
		}
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
	};

	processed_data.schedule_assignments = data.schedule_assignments;
	
	var Resources = ESP.Scheduling.Resources;

	// resourcetypes
	for (var i = 0; i < data.resourcetypes.length; i++) {
	    var rt = data.resourcetypes[i];
	    Resources.create('RoomResource', { uid: rt.uid, text: rt.name, description: rt.description, attributes: rt.attributes });
	}

	// times
	for (var i = 0; i < data.times.length; i++) {
	    var t = data.times[i];
	    // constructors for native classes can't be called via apply()... :-(
	    var start = new Date(t.start[0],t.start[1],t.start[2],t.start[3],t.start[4],t.start[5]).getTime();
	    var end = new Date(t.end[0],t.end[1],t.end[2],t.end[3],t.end[4],t.end[5]).getTime();
	    processed_data.times.push(
	            Resources.create('Time',
				     { uid: t.id, text: t.short_description, start: start, end: end, length: end - start + 10*60000 }));
	}
	processed_data.times.sort(function(x,y){
		return x.start - y.start;
	    });
	for (var i = 0; i < processed_data.times.length - 1; i++) {
	    var t = processed_data.times[i];
	    var t2 = processed_data.times[i+1];
	    t.seq = Resources.Time.sequential(t,t2) ? t2 : null;
	}
	
	// rooms / blocks
	var BlockStatus = Resources.BlockStatus;
	for (var i = 0; i < data.rooms.length; i++) {
	    var r = data.rooms[i];
	    var room;
	    processed_data.rooms.push( room =
				       Resources.create('Room',{ uid: r.uid, text: r.text, block_contents: ESP.Utilities.genPopup(r.text, {'Size:': r.num_students.toString(), 'Resources:': r.associated_resources.map(function(x){ return Resources.get('RoomResource',x).text; })}, true)})).uid;
	    var rid = room.uid
	    processed_data.block_index[rid] = {};
	    for (var j = 0; j < r.availability.length; j++) {
		var t = Resources.get('Time', r.availability[j]);
		var block;
		processed_data.blocks.push(block = Resources.create(
		    'Block', { time: t, room: r, status:BlockStatus.AVAILABLE, uid: [t.uid,r.uid] }));
		processed_data.block_index[rid][block.time.uid] = block;
	    }
	}
	for (var i = 0; i < processed_data.blocks.length; i++) {
	    var b = processed_data.blocks[i];
	    b.seq = b.time.seq ? processed_data.block_index[b.room.uid][b.time.seq.uid] : null;
	}
	processed_data.rooms.sort(function(x,y){
		return x.uid < y.uid ? -1 : x.uid == y.uid ? 0 : 1;
	    });
	
	// teachers
	for (var i = 0; i < data.teachers.length; i++) {
	    var t = data.teachers[i];
	    processed_data.teachers.push(Resources.create('Teacher',{
		uid: t.uid, text: t.text, block_contents: ESP.Utilities.genPopup(t.text, {'Available Times:': t.availability.map(function(x){ return Resources.get('Time',x).text; }) }, true),
			available_times: t.availability.map(function(x){ return Resources.get('Time',x); }),
			sections: []
		    }));
	}
	
	// sections
	for (var i = 0; i < data.sections.length; i++) {
	    var c = data.sections[i];
	    var s;
	    processed_data.sections.push(s = Resources.create('Section',{
		    uid: c.id,
		    class_id: c.class_id,
		    code: c.emailcode,
		    block_contents: ESP.Utilities.genPopup(c.emailcode, {
		      'Size:': c.max_class_capacity ? c.max_class_capacity : "(unspecified)",
		      'Resources:': c.resource_requests.map(function(x){ return (Resources.get('RoomResource', x[0]) ? (Resources.get('RoomResource', x[0]).text + ": " + x[1]) : null); }),
		      'Optimal Size:': c.optimal_class_size ? c.optimal_class_size.toString() : "(unspecified)",
		      'Optimal Range:': c.optimal_class_size_range,
		      'Allowable Ranges:': c.allowable_class_size_ranges }, true),
		    category: c.category,
		    length: Math.round(c.length*10)*3600000/10 + 600000, // convert hr to ms
		    length_hr: Math.round(c.length * 2) / 2,
		    id:c.id,
		    status:c.status,
		    text:c.text,
		    teachers:c.teachers.map(function(x){ return Resources.get('Teacher',x); }),
		    }));
	    s.teachers.map(function(x){ x.sections.push(s); });
	}
	
	return processed_data;
    };
    
    var apply_existing_classes = function(assignments, data) {
	var Resources = ESP.Scheduling.Resources;
	var rsrc_sec = {}
	var sa;

	for (var i = 0; i < assignments.length; i++) {
	    sa = data.schedule_assignments[i];

	    if (!(rsrc_sec[sa.classsection_id])) {
		rsrc_sec[sa.classsection_id] = [];
	    }

	    rsrc_sec[sa.classsection_id].push(Resources.get('Block', [sa.resource_time_id,sa.resource_id]));
 	}

	var Section;
	var sec_id;
	for (var i = 0; i < data.sections.length; i++) {
	    sec_id = data.sections[i].uid;
	    if (rsrc_sec[sec_id]) {
		ESP.Utilities.evm.fire('block_section_assignment_request', { 
			section: Resources.get('Section', sec_id), 
			    blocks: rsrc_sec[sec_id],
			    nowriteback: true /* Don't tell the server about this assignment */ });
	    }
	}
    }

    var validate_block_assignment = function(block, section) {
	// check status
	if (block.status != ESP.Scheduling.Resources.BlockStatus.AVAILABLE) {
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
		return false;
	}

	// check for teacher class conflicts
	for (var i = 0; i < section.teachers.length; i++) {
	    var teacher = section.teachers[i];
	    for (var j = 0; j < teacher.sections.length; j++) {
		var other_section = teacher.sections[j];
		if (other_section == section) continue;
		for (var k = 0; k < other_section.blocks.length; k++) {
		    if (other_section.blocks[k].time == time) {
			return false;
		    }
		}
	    }
	}

	return true;
    };
    
    var self = {
	init: init,
	validate_block_assignment: validate_block_assignment
    };
    return self;
}();


/*
 * initialize the page
 */
$j(function(){
	var version_uuid = null;
	ESP.version_uuid = version_uuid;

	$j.getJSON('ajax_schedule_last_changed', function(d, status) {
		if (status == "success") {
		    ESP.version_uuid = d['val'];
		}
	    });

	var data = {};
	var success_count = 0;
	var files = ['times','rooms','sections','resources','resourcetypes','teachers','schedule_assignments'];
	var ajax_verify = function(name) {
	    return function(d, status) {
		if (status != "success") {
		    alert(status + '[' + name + ']');
		} else {
		    data[name] = d;
		    if (++success_count == files.length) {
			ESP.Scheduling.init(data);
		    }
		}
	    };
	};
	var ajax_retry = function(name) {
	    return function(xhtr, textStatus, errorThrown) {
		if (textStatus == "timeout" || textStatus == "error") {
		    setTimeout(function() {
			    $j.ajax({url: 'ajax_' + name, dataType: 'json', success: ajax_verify(name), error: ajax_retry(name)});
			}, 1000);
		} else if (textStatus == "parsererror") {
		    alert("Error:  Invalid JSON data from '" + name + "'!");
		} else if (textStatus == "notmodified") {
		    console.log("textStatus == 'notmodified'.  What, this actually happens?");
		} else {
		    alert("Server reported unknown error condition: " + textStatus);
		}
	    }
	}
	for (var i = 0; i < files.length; i++) {
	    $j.ajax({url: 'ajax_' + files[i], dataType: 'json', success: ajax_verify(files[i]), error: ajax_retry(files[i])});
	}


	setInterval(function() {
		ESP.Scheduling.status('warning','Pinging server...');
		$j.getJSON('ajax_schedule_last_changed', function(d, status) {
			if (status == "success") {
			    ESP.Scheduling.status('success','Refreshed data from server.');
			    if (d['val'] != ESP.version_uuid) {
				success_count = 0;
				ESP.version_uuid = d['val'];
				data = {};
				for (var i = 0; i < files.length; i++) {
				    $j.getJSON('ajax_' + files[i], ajax_verify(files[i]));
				}
			    }
			} else {
			    ESP.Scheduling.status('error','Unable to refresh data from server.');
			}
		    });
	    }, 300000);
});
