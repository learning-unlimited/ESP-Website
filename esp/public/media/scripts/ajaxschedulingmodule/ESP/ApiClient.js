function ApiClient() {
    this.schedule_section = function(section_id, timeslot_ids, room_name, callback, errorReporter){
	assignments = timeslot_ids.map(function(id) {
	    return id + "," + room_name;
	}).join("\n");

        var req = { 
	    action: 'assignreg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id,
            block_room_assignments: assignments
	};
	return this.send_request(req, callback, errorReporter);
    };

    this.unschedule_section = function(section_id, callback, errorReporter){
	var req = { 
	    action: 'deletereg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id
	};
	this.send_request(req, callback, errorReporter);
    };

    this.send_request = function(req, callback, errorReporter){
        $j.post('ajax_schedule_class', req, "json")
        .success(function(ajax_data, status) {
	    if (ajax_data.ret){
		console.log("success");
		callback();
	    }
	    else {
		console.log("failure");
		errorReporter(ajax_data.msg);
	    }
	})
	.error(function(ajax_data, status) {
	    console.log("error");
	    errorReporter("An error occurred saving the schedule change.");
	    return false
	});
    };
}
