function ApiClient() {
    /**
     * Fetch the change log from the server
     * 
     * @param last_fetched_index: The previous index we retrieved from the server
     * @param callback: If successful, this function will be called. Takes one param
     *                  ajax_data which is the data that was fetched.
     * @param: errorReporter: If server reports an error, this function will be called.
     *                        Takes one param msg with an error message.
     */
    this.get_change_log = function(last_fetched_index, callback, errorReporter){
	    $j.getJSON(
	        'ajax_change_log',
	        { 'last_fetched_index': last_fetched_index })
	        .success(function(ajax_data, status) {
	            callback(ajax_data);
	        })
	        .error(function(ajax_data, status) {
	            errorReporter("An error occurred fetching the changelog.");
	        });
    }

    /**
     * Schedule a section on the server.
     *
     * @param section_id: The ID of the section to schedule
     * @param timeslot_ids: A list of ids of all timeslots the class should be scheduled during.
     * @param room_name: The name of the room (its ID).
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
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

    /**
     * Unschedule a section on the server.
     *
     * @param section_id: The ID of the section to schedule
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
    this.unschedule_section = function(section_id, callback, errorReporter){
	    var req = { 
	        action: 'deletereg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id
	    };
	    this.send_request(req, callback, errorReporter);
    };

    /**
     * Send a request to the server
     *
     * @param req: The object to send to the server.
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
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
	        });
    };
}
