function ApiClient(){
    this.schedule_section = function(section_id, timeslot_id, room_name){
        var req = { 
	    action: 'assignreg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id,
            block_room_assignments: timeslot_id + "," + room_name
	}
	return this.send_request(req)
    }

    this.unschedule_section = function(section_id){
	var req = { 
	    action: 'deletereg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id
	};
	return this.send_request(req)
    }

    this.send_request = function(req){
        var success = $j.post('ajax_schedule_class', req, "json")
        .success(function(ajax_data, status) {
	    return true
	})
	.error(function(ajax_data, status) {
	    return false
	})
	return success
    }
}
