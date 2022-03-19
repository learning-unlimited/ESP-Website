function ApiClient() {
    /**
     * Fetch the change log from the server using ajax calls to the python views
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
            .done(function(ajax_data, status) {
                callback(ajax_data);
            })
            .fail(function(ajax_data, status) {
                errorReporter("An error occurred fetching the changelog.");
            });
    }

    /**
     * Set a scheduling comment on a section.
     *
     * @param section_id: the section to set comment on
     * @param comment: comment to set, or blank for no comment
     * @param locked: true/false whether to lock the section from further scheduling
     * @param callback(): called on success
     * @param errorReporter(err): called on error with string error message
     */
    this.set_comment = function(section_id, comment, locked, callback, errorReporter) {
        params = {
            'cls': section_id,
            'comment': comment,
            'csrfmiddlewaretoken': csrf_token(),
        };
        if(locked) {
            params['locked'] = 'yes';
        }
        $j.post('ajax_set_comment', params).done(function() {
            callback();
        }).fail(function() {
            errorReporter('An error occurred setting comment.');
        });
    };

    /**
     * Schedule a section on the server.
     *
     * @param section_id: The ID of the section to schedule
     * @param timeslot_ids: A list of ids of all timeslots the class should be scheduled during.
     * @param room_id: The id of the room.
     * @param override: Should teacher availability be overriden?
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
    this.schedule_section = function(section_id, timeslot_ids, room_id, override, callback, errorReporter){
        assignments = timeslot_ids.map(function(id) {
            return id + "," + room_id;
        }).join("\n");

        var req = {
            action: 'assignreg',
            csrfmiddlewaretoken: csrf_token(),
            cls: section_id,
            block_room_assignments: assignments,
            override: override
        };
        return this.send_request('ajax_schedule_class', req, callback, errorReporter);
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
        this.send_request('ajax_schedule_class', req, callback, errorReporter);
    };

    /**
     * Swap two sets of sections on the server.
     *
     * @param assignments1: List of new assignments for the section(s) in room 1
     * @param assignments2: List of new assignments for the section(s) in room 2
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
    this.swap_sections = function(assignments1, assignments2, override, callback, errorReporter){
        var req = {
            action: 'swap',
            csrfmiddlewaretoken: csrf_token(),
            assignments: JSON.stringify(assignments1.concat(assignments2)),
            override: override
        };
        this.send_request('ajax_schedule_class', req, callback, errorReporter);
    };

    /**
     * Assign a moderator to a section on the server.
     *
     * @param section_id: The ID of the section to which to assign a moderator.
     * @param room_id: The ID of the moderator to assign.
     * @param override: Should teacher/moderator availability be overriden?
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
    this.assign_moderator = function(section_id, moderator_id, override, callback, errorReporter){
        var req = {
            action: 'assignmod',
            csrfmiddlewaretoken: csrf_token(),
            sec: section_id,
            mod: moderator_id,
            override: override
        };
        return this.send_request('ajax_assign_moderator', req, callback, errorReporter);
    };

    /**
     * Unassign a moderator from a section on the server.
     *
     * @param section_id: The ID of the section from which to unassign the moderator
     * @param moderator_id: The ID of the moderator to unassign from the section
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
    this.unassign_moderator = function(section_id, moderator_id, callback, errorReporter){
        var req = {
            action: 'removemod',
            csrfmiddlewaretoken: csrf_token(),
            sec: section_id,
            mod: moderator_id
        };
        this.send_request('ajax_assign_moderator', req, callback, errorReporter);
    };

    /**
     * Send a request to the server
     *
     * @param fnc: The view to post to
     * @param req: The object to send to the server.
     * @param callback: If successful, this function will be called. Takes no params.
     * @param errorReporter: If server reports an error, this function will be called.
     *                       Takes one param msg with an error message.
     */
    this.send_request = function(fnc, req, callback, errorReporter){
        $j.post(fnc, req, "json")
            .done(function(ajax_data, status) {
                if (ajax_data.ret){
                    console.log("success");
                    callback();
                }
                else {
                    console.log("failure");
                    errorReporter(ajax_data.msg);
                }
            })
            .fail(function(ajax_data, status) {
                console.log("error");
                errorReporter("An error occurred while attempting the requested change.");
            });
    };
}
