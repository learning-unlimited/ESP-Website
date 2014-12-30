function Matrix(
    timeslots,
    rooms,
    teachers,
    schedule_assignments,
    sections,
    el,
    garbage_el,
    messagePanel,
    section_info_el,
    api_client
){ 
    this.el = el;
    this.garbage_el = garbage_el;
    this.messagePanel = messagePanel;
    this.section_info_el = section_info_el;
    this.currently_selected = null;
    this.el.id = "matrix-table";

    this.rooms = rooms;
    this.teachers = teachers;
    this.schedule_assignments = schedule_assignments;
    this.sections = sections;
    this.timeslots = new Timeslots(timeslots);

    this.api_client = api_client;

    // Initialize handlers for droppable elements

    // garbage stuff
    this.garbageDropHandler = function(ev, ui){
	    this.unscheduleSection(ui.draggable.data("section").id);
    }.bind(this);

    // set up drophandler
    this.dropHandler = function(el, ui){
	    var cell = $j(el.currentTarget).data("cell");
	    var section = ui.draggable.data("section");
	    this.scheduleSection(section.id, cell.room_name, cell.timeslot_id);
    }.bind(this);

    this.init = function(){
	    this.el.on("drop", "td", this.dropHandler);
	    this.garbage_el.droppable({
	        drop: this.garbageDropHandler
	    });
        this.el.on("click", "td > a", function(evt, ui) {
            var cell = $j(evt.currentTarget.parentElement).data("cell");
            if(this.currently_selected === cell) {
                cell.unselect();
            } else {
                if(this.currently_selected) {
                    this.currently_selected.unselect();
                }
                cell.select();
            }
        }.bind(this)); 
    }

    this.init();

    // set up cells
    var matrix = this;
    this.cells = function(){
        // cells has room names as keys and arrays of timeslots as values
	    var cells = {};
	    $j.each(rooms, function(room_name, room){
	        cells[room_name] = [];
	        i = 0;
	        $j.each(timeslots, function(timeslot_id_string, timeslot){
		        var timeslot_id = parseInt(timeslot_id_string);
		        if (room.availability.indexOf(timeslot_id) >= 0){
		            cells[room_name][i] = new Cell($j("<td/>"), null, room_name, timeslot_id, matrix);
		        } else {
		            cells[room_name][i] = new DisabledCell($j("<td/>"))
		        }
		        i = i + 1;
	        });
	    });

        // Associated already scheduled classes with rooms
	    $j.each(schedule_assignments, function(class_id, assignment_data){
	        $j.each(assignment_data.timeslots, function(j, timeslot_id){
		        var class_emailcode = sections[class_id].emailcode;
		        var timeslot_order = timeslots[timeslot_id].order;
		        cells[assignment_data.room_name][timeslot_order].addSection(sections[class_id]);
	        });
	    });
	    return cells;
    }();

    /**
     * Gets the cell that represents room_name and timeslot_id
     */
    this.getCell = function(room_name, timeslot_id){
	    return this.cells[room_name][this.timeslots.get_by_id(timeslot_id).order];
    };

    this.getAvailableTimeslotsForSection = function(section) {
        var availabilities = [];
        var already_teaching = [];        
        $j.each(section.teachers, function(index, teacher_id) {
            var teacher = this.teachers[teacher_id];
            var teacher_availabilities = teacher.availability.slice();
            var sections = teacher.sections;
            $j.each(sections, function(index, section_id) {
                var assignment = this.schedule_assignments[section_id];
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
     * Checks a section we want to schedule in room_name during schedule_timeslots
     * to make sure the room is available during that time and the length is nonzero.
     *
     * Returns an object with property valid that is set to whether the assignment is valid
     * and reason which contains a message if valid is false.
     */
    this.validateAssignment = function(section, room_name, schedule_timeslots){
        var result = {
            valid: true,
            reason: null,
        }
	    if (!schedule_timeslots){
            result.valid = false;
            result.reason = "Error: Not scheduled during a timeblock";
	        return result;
	    }

	    for(timeslot_index in schedule_timeslots){
	        var timeslot_id = schedule_timeslots[timeslot_index];
	        if (this.getCell(room_name, timeslot_id).section != null){
                result.valid = false;
                result.reason = "Error: timeslot" +  this.timeslots[timeslot_id] + 
                    " already has a class in " + room_name + "."
		        return result;
	        }
	    }
	    return result;
    };

    /**
     * Schedule a section of a class into room_name starting with first_timeslot_id
     */
    this.scheduleSection = function(section_id, room_name, first_timeslot_id){
        var old_assignment = this.schedule_assignments[section_id];
	    var section = this.sections[section_id]
	    var schedule_timeslots = this.timeslots.get_timeslots_to_schedule_section(section, first_timeslot_id);
	    if (!this.validateAssignment(section, room_name, schedule_timeslots).valid){
	        return;
	    }
		this.scheduleSectionLocal(section_id, room_name, schedule_timeslots);
	    this.api_client.schedule_section(
	        section.id,
	        schedule_timeslots,
	        room_name, 
	        function() {

	        }.bind(this),
	        function(msg) {
                this.scheduleSectionLocal(section_id, old_assignment.room_name, old_assignment.timeslots);
                this.messagePanel.addMessage("Error: " + msg)
		        console.log(msg);
	        }.bind(this)
	    );
    }


    /**
     * Make the local changes associated with scheduling a class and update the display
     */
    this.scheduleSectionLocal = function(section_id, room_name, schedule_timeslots){
	    var old_assignment = this.schedule_assignments[section_id];
	    var section = this.sections[section_id];

	    if(
	        old_assignment.room_name == room_name &&
	            JSON.stringify(old_assignment.timeslots)==JSON.stringify(schedule_timeslots)
	    ){
	        return;
	    }
        
        // Add section to cells
	    for(timeslot_index in schedule_timeslots){
	        var timeslot_id = schedule_timeslots[timeslot_index];
	        this.getCell(room_name, timeslot_id).addSection(section);
	    }

	    // Unschedule from old place
	    for (timeslot_index in old_assignment.timeslots) {
	        var timeslot_id = old_assignment.timeslots[timeslot_index];
	        var cell = this.getCell(old_assignment.room_name, timeslot_id);
	        cell.removeSection();
	    }
        
	    this.schedule_assignments[section.id] = {
	        room_name: room_name,
	        timeslots: schedule_timeslots,
	        id: section.id
	    };

	    $j("body").trigger("schedule-changed");
    }


    /**
     * Unschedule a section of a class
     */
    this.unscheduleSection = function(section_id){
        var old_assignment = this.schedule_assignments[section_id];
        var old_room_name = old_assignment.room_name;
        var old_schedule_timeslots = old_assignment.timeslots;
		this.unscheduleSectionLocal(section_id);        
	    this.api_client.unschedule_section(
	        section_id,
	        function(){ 
	        }.bind(this),
	        function(msg){
                this.scheduleSectionLocal(section_id, old_room_name, old_schedule_timeslots);
                this.messagePanel.addMessage("Error: " + msg);
		        console.log(msg);
	        }.bind(this)
	    );
    };

    /**
     * Update the local interface to reflect unscheduling a class
     */
    this.unscheduleSectionLocal = function(section_id) {
	    this.scheduleSectionLocal(section_id, null, [])
    };

    /**
     * Remove a section from a cell
     */
    this.clearCell = function(cell){
	    cell.removeSection();
    };


    /**
     * Return the text of a room tooltip
     */
    this.tooltip = function(room) {
        var tooltip_parts = [
            "<b>" + room.text + "</b>",
            "Capacity: " + room.num_students + " students",
        ];
        return tooltip_parts.join("</br>");
    };

    // render
    this.render = function(){
	    var table = $j("<table/>");

	    //Time headers
	    var header_row = $j("<tr/>").appendTo($j("<thead/>").appendTo(table));
	    $j("<th/>").appendTo(header_row);
	    $j.each(timeslots, function(id, timeslot){
	        $j("<th>" + timeslot.label + "</th>").appendTo(header_row);
	    });

	    //Room headers
	    var rows = {};	//table rows by room name
	    $j.each(this.rooms, function(id, room){
            var room_header = $j("<th>" + id + "</th>");
            room_header.tooltip({
                content: this.tooltip(room),
                items: "th",
            });
	        var row = $j("<tr></tr>");
            room_header.appendTo(row);
	        rows[id] = row;
	        row.appendTo(table);
	    }.bind(this));

	    //populate cells
	    var cells = this.cells;
	    $j.each(this.rooms, function(id, room){
	        row = rows[id];
	        for(i = 0; i < Object.keys(timeslots).length; i++){
		        cells[id][i].el.appendTo(row);
	        }
	    });
	    table.appendTo(this.el);
    };
};

