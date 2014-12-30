function Sections(sections_data, teacher_data, scheduleAssignments, apiClient) {
    this.scheduleAssignments = scheduleAssignments;
    this.apiClient = apiClient;
    this.sections_data = sections_data;

    this.init = function() {
        $j.each(sections_data, function(section_id, section) {
            section.teacher_data = []
            $j.each(section.teachers, function(index, teacher_id) {
                section.teacher_data.push(teacher_data[teacher_id]);
            });
        });
    };

    this.init();

    this.bindMatrix = function(matrix) {
        this.matrix = matrix;
    }

    this.getById = function(section_id) {
        return sections_data[section_id];
    };

    this.getAvailableTimeslots = function(section) {
        var availabilities = [];
        var already_teaching = [];        
        $j.each(section.teacher_data, function(index, teacher) {
            var teacher_availabilities = teacher.availability.slice();
            $j.each(teacher.sections, function(index, section_id) {
                var assignment = this.scheduleAssignments[section_id];
                if(assignment && section_id != section.id) {
                    $j.each(assignment.timeslots, function(index, timeslot_id) {
                        var availability_index = teacher_availabilities.indexOf(timeslot_id);
                        if(availability_index >= 0) {
                            teacher_availabilities.splice(availability_index, 1);
                            already_teaching.push(timeslot_id);
                        }
                    }.bind(this));
                }
            }.bind(this));
            availabilities.push(teacher_availabilities);
        }.bind(this));
        var availableTimeslots = helpersIntersection(availabilities, true);
        return [availableTimeslots, already_teaching];
    };

    this.getTeachersString = function(section) {
        var teacher_list = []
        $j.each(section.teacher_data, function(index, teacher) {
            teacher_list.push(teacher.first_name + " " + teacher.last_name);
        });
        var teachers = teacher_list.join(", ");
        return teachers;
    };

    /**
     * Schedule a section of a class into room_name starting with first_timeslot_id
     */
    this.scheduleSection = function(section, room_name, first_timeslot_id){
        var old_assignment = this.scheduleAssignments[section.id];
	    var schedule_timeslots = this.matrix.timeslots.get_timeslots_to_schedule_section(section, first_timeslot_id);
	    if (!this.matrix.validateAssignment(section, room_name, schedule_timeslots).valid){
	        return;
	    }
		this.scheduleSectionLocal(section, room_name, schedule_timeslots);
	    this.apiClient.schedule_section(
	        section.id,
	        schedule_timeslots,
	        room_name, 
	        function() {

	        },
	        function(msg) {
                this.scheduleSectionLocal(section, old_assignment.room_name, old_assignment.timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg)
		        console.log(msg);
	        }.bind(this)
	    );
    }


    /**
     * Make the local changes associated with scheduling a class and update the display
     */
    this.scheduleSectionLocal = function(section, room_name, schedule_timeslots){
	    var old_assignment = this.scheduleAssignments[section.id];
	    if(
	        old_assignment.room_name == room_name &&
	            JSON.stringify(old_assignment.timeslots)==JSON.stringify(schedule_timeslots)
	    ){
	        return;
	    }
        
        // Add section to cells
	    for(timeslot_index in schedule_timeslots){
	        var timeslot_id = schedule_timeslots[timeslot_index];
	        this.matrix.getCell(room_name, timeslot_id).addSection(section);
	    }

	    // Unschedule from old place
	    for (timeslot_index in old_assignment.timeslots) {
	        var timeslot_id = old_assignment.timeslots[timeslot_index];
	        var cell = this.matrix.getCell(old_assignment.room_name, timeslot_id);
	        cell.removeSection();
	    }
        
	    this.scheduleAssignments[section.id] = {
	        room_name: room_name,
	        timeslots: schedule_timeslots,
	        id: section.id
	    };

	    $j("body").trigger("schedule-changed");
    }


    /**
     * Unschedule a section of a class
     */
    this.unscheduleSection = function(section){
        var old_assignment = this.scheduleAssignments[section.id];
        var old_room_name = old_assignment.room_name;
        var old_schedule_timeslots = old_assignment.timeslots;
		this.unscheduleSectionLocal(section);
	    this.apiClient.unschedule_section(
	        section.id,
	        function(){ 
	        },
	        function(msg){
                this.scheduleSectionLocal(section, old_room_name, old_schedule_timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg);
		        console.log(msg);
	        }.bind(this)
	    );
    };

    /**
     * Update the local interface to reflect unscheduling a class
     */
    this.unscheduleSectionLocal = function(section) {
	    this.scheduleSectionLocal(section, null, [])
    };




}
