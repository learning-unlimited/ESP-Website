/**
 * Stores the section data and provides helper methods for accessing and scheduling
 * sections.
 * 
 * @params sections_data: The raw section data
 * @params teacher_data: The raw teacher data for populating the sections
 * @params scheduleAssignments: The scheule assignments
 * @params apiClient: The object that can communicate with the server
 */
function Sections(sections_data, teacher_data, scheduleAssignments, apiClient) {
    this.sections_data = sections_data;
    this.scheduleAssignments = scheduleAssignments;
    this.apiClient = apiClient;

    // The section that is currently selected
    this.selectedSection = null;
    
    this.availableTimeslots = [];

    /**
     * Populate the sections data with teacher info
     */
    this.init = function() {
        $j.each(sections_data, function(section_id, section) {
            section.teacher_data = []
            $j.each(section.teachers, function(index, teacher_id) {
                section.teacher_data.push(teacher_data[teacher_id]);
            });
        });
    };

    this.init();

    /**
     * Bind a matrix to the sections to allow the scheduling methods to work
     * 
     * @param matrix: The matrix to bind
     */
    this.bindMatrix = function(matrix) {
        this.matrix = matrix;
    }

    /**
     * Get a section by its ID
     *
     * @param section_id: The id of the section to get
     */
    this.getById = function(section_id) {
        return sections_data[section_id];
    };

    /**
     * Get the sections that are not yet scheduled
     */
    this.filtered_sections = function(){
        var returned_sections = [];
        $j.each(this.sections_data, function(section_id, section) {
            if (
                this.scheduleAssignments[section.id] && 
                this.scheduleAssignments[section.id].room_name == null
            ){
                returned_sections.push(section);
            }
        }.bind(this));
        return returned_sections;
    };

    /**
     * Select the cells associated with this section, put it on the section info
     * panel, and highlight the available cells to place the section.
     *
     * @param section: The section to select 
     */
    this.selectSection = function(section) {
        if(this.selectedSection) {
            if(this.selectedSection === section) {
                this.unselectSection();
                return;
            } else {
                this.unselectSection();
            }
        }

        var assignment = this.scheduleAssignments[section.id];
        if(assignment.room_name) {
            $j.each(assignment.timeslots, function(index, timeslot) {
                var cell = this.matrix.getCell(assignment.room_name, timeslot);
                cell.select();
            }.bind(this));
        } else {
            section.directoryCell.select();
        }
        this.selectedSection = section;
        this.matrix.sectionInfoPanel.displaySection(section);
        this.availableTimeslots = this.getAvailableTimeslots(section);
        this.matrix.highlightTimeslots(this.availableTimeslots);


    };

    /**
     * Unselect the cells associated with the currently selected section, hide the section info
     * panel, and unhighlight the available cells to place the section.
     */ 
    this.unselectSection = function() {
        if(!this.selectedSection) {
            return;
        }
        var assignment = this.scheduleAssignments[this.selectedSection.id];
        if(assignment.room_name) {
            $j.each(assignment.timeslots, function(index, timeslot) {
                var cell = this.matrix.getCell(assignment.room_name, timeslot);
                cell.unselect();
            }.bind(this));
        } else {
            this.selectedSection.directoryCell.unselect();
        }

        this.selectedSection = null;
        this.matrix.sectionInfoPanel.hide();
        this.matrix.unhighlightTimeslots(this.availableTimeslots);

    };

    /**
     * Get the timeslots available for scheduling this section.
     * Returns an array of two lists. 
     *
     * The first has all the timeslots where all teachers are available and 
     * none are teaching.
     *
     * The second has all the timeslots where teachers are available but already teaching
     *
     * @param section: The section to check availability.
     */
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

    /**
     * Get the teachers for a section as a list separated by a comma
     *
     * @param section: The section to get the teachers from.
     */
    this.getTeachersString = function(section) {
        var teacher_list = []
        $j.each(section.teacher_data, function(index, teacher) {
            teacher_list.push(teacher.first_name + " " + teacher.last_name);
        });
        var teachers = teacher_list.join(", ");
        return teachers;
    };

    /**
     * Schedule a section of a class.
     * 
     * @param section: The section to schedule
     * @param room_name: The name of the room to schedule it in
     * @param first_timeslot_id: The ID of the first timeslot to schedule the section in
     */
    this.scheduleSection = function(section, room_name, first_timeslot_id){
        var old_assignment = this.scheduleAssignments[section.id];
        var schedule_timeslots = this.matrix.timeslots.
                                      get_timeslots_to_schedule_section(section, first_timeslot_id);
        
        // Make sure the assignment is valid
        if (!this.matrix.validateAssignment(section, room_name, schedule_timeslots).valid){
            return;
        }
        
        // Optimistically schedule the section locally before hearing back from the server
        this.scheduleSectionLocal(section, room_name, schedule_timeslots);
        this.apiClient.schedule_section(
            section.id,
            schedule_timeslots,
            room_name, 
            function() {},
            // If there's an error, reschedule the section in its old location
	        function(msg) {
                this.scheduleSectionLocal(section, 
                                          old_assignment.room_name, 
                                          old_assignment.timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg)
		        console.log(msg);
	        }.bind(this)
	    );
    }


    /**
     * Make the local changes associated with scheduling a class and update the display
     *
     * @param section: The section to schedule
     * @param room_name: The name of the room to schedule it in
     * @param schedule_timeslots: The IDs of the timeslots to schedule the section in     *
     */
    this.scheduleSectionLocal = function(section, room_name, schedule_timeslots){
	    var old_assignment = this.scheduleAssignments[section.id];

        // Check to see if we need to make any changes
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
        if(this.selectedSection === section) {
            this.unselectSection();
        }

        // Update the array that keeps track of the assignments
	    this.scheduleAssignments[section.id] = {
	        room_name: room_name,
	        timeslots: schedule_timeslots,
	        id: section.id
	    };

        // Trigger the event that tells the directory to update itself.
	    $j("body").trigger("schedule-changed");
    }


    /**
     * Unschedule a section of a class.
     *
     * @param section: the section to unschedule
     */
    this.unscheduleSection = function(section){
        var old_assignment = this.scheduleAssignments[section.id];
        var old_room_name = old_assignment.room_name;
        var old_schedule_timeslots = old_assignment.timeslots;

        // Optimistically make local changes to unschedule the class
		this.unscheduleSectionLocal(section);
	    this.apiClient.unschedule_section(
	        section.id,
	        function(){ 
	        },
            // If the server returns an error, put the class back in its original spot
	        function(msg){
                this.scheduleSectionLocal(section, old_room_name, old_schedule_timeslots);
                this.matrix.messagePanel.addMessage("Error: " + msg);
		        console.log(msg);
	        }.bind(this)
	    );
    };

    /**
     * Update the local interface to reflect unscheduling a class
     *
     * @param section: the section to unschedule
     */
    this.unscheduleSectionLocal = function(section) {
	    this.scheduleSectionLocal(section, null, [])
    };


    this.getBaseUrlString = function() {
        var parser = document.createElement('a');
        parser.href = document.URL;
        return parser.pathname.slice(0, -("ajaxscheduling".length) - 1);
    };

}
