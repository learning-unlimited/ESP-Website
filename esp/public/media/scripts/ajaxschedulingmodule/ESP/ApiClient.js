function ApiClient(){
    this.schedule_section = function(section_id, timeslot_id, room_name, callback){
        var req = { 
	    action: 'assignreg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id,
            block_room_assignments: timeslot_id + "," + room_name
	}
	return this.send_request(req, callback)
    }

    this.unschedule_section = function(section_id, callback){
	var req = { 
	    action: 'deletereg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id
	};
	this.send_request(req, callback)
    }

    this.send_request = function(req, callback){
        $j.post('ajax_schedule_class', req, "json")
        .success(function(ajax_data, status) {
	    if (ajax_data.ret){
		console.log("success")
		callback()
	    }
	})
	.error(function(ajax_data, status) {
	    console.log("failure")
	    return false
	})
    }
}
