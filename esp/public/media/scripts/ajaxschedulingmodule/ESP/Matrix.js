/**
 * The grid of cells that displays the schedule.
 * 
 * @param timeslots: A Timeslots object corresponding to times available for classes
 * @param rooms: The rooms that are available for scheduling. Keys are ids values are room data.
 * @param sections: A list of all sections for the program
 * @param el: The element to morph into the matrix
 * @param messsagePanel: The panel that can display messages and errors
 * @param secionInfoPanel: The panel that displays section info
 */
function Matrix(
    timeslots,
    rooms,
    sections,
    el,
    messagePanel,
    sectionInfoPanel
){ 
    this.el = el;
    this.el.id = "matrix-table";

    this.timeslots = timeslots;
    this.rooms = rooms;

    this.sections = sections;
    this.sections.bindMatrix(this);

    this.messagePanel = messagePanel;
    this.sectionInfoPanel = sectionInfoPanel;

    /**
     * Initialize the matrix
     */
    this.init = function(){
        // set up cells
        var matrix = this;
        this.cells = function(){
            // cells has room names as keys to the outer object and timeslots as keys to the
            // inner object
	        var cells = {};
	        $j.each(rooms, function(room_name, room){
	            cells[room_name] = [];
	            i = 0;
	            $j.each(this.timeslots.timeslots, function(timeslot_id_string, timeslot){
		            var timeslot_id = parseInt(timeslot_id_string);
		            if (room.availability.indexOf(timeslot_id) >= 0){
		                cells[room_name][i] = new Cell($j("<td/>"), null, room_name, 
                                                       timeslot_id, matrix);
		            } else {
		                cells[room_name][i] = new DisabledCell($j("<td/>"), room_name, 
                                                               timeslot_id)
		            }
		            i = i + 1;
	            }.bind(this));
	        }.bind(this));
            return cells;
        }.bind(this)();

        // set up handlers for selecting and scheduling classes
        this.el.on("click", "td > a", function(evt, ui) {
            var cell = $j(evt.currentTarget.parentElement).data("cell");
            this.sections.selectSection(cell.section);
        }.bind(this)); 
        this.el.on("click", "td.teacher-available-cell", function(evt, ui) {
            var cell = $j(evt.currentTarget).data("cell");
            if(this.sections.selectedSection) {
                this.sections.scheduleSection(this.sections.selectedSection, 
                                              cell.room_name, cell.timeslot_id);
            }
        }.bind(this));


    };

    this.init();
    
    /**
     * Highlight the timeslots on the grid.
     *
     * @param timeslots: A 2-d array. The first element is an array of
     *                   timeslots where all teachers are completely available. 
     *                   The second is an array of timeslots where one or more 
     *                   teachers are teaching, but would be available otherwise.
     */
    //TODO: Move this to Matrix.js
    this.highlightTimeslots = function(timeslots) {
        /**
         * Adds a class to all non-disabled cells corresponding to each
         * timeslot in timeslots.
         *
         * @param timeslots: A 1-d array of tiemslot IDs
         * @param className: The class to add to the cells
         */
        addClassToTimeslots = function(timeslots, className) {
            $j.each(timeslots, function(j, timeslot) {
                $j.each(this.rooms, function(k, room) {
                    var cell = this.getCell(room.id, timeslot);
                    if(!cell.section && !cell.disabled) {
                        cell.el.addClass(className);
                    } 
                }.bind(this));
            }.bind(this));
        }.bind(this);

        var available_timeslots = timeslots[0];
        var teaching_timeslots = timeslots[1];
        addClassToTimeslots(available_timeslots, "teacher-available-cell");
        addClassToTimeslots(teaching_timeslots, "teacher-teaching-cell");
    }

    /**
     * Unhighlight the cells that are currently highlighted
     *
     * @param timeslots: A 2-d array. The first element is an array of
     *                   timeslots where all teachers are completely available. 
     *                   The second is an array of timeslots where one or more 
     *                   teachers are teaching, but would be available otherwise.
     */
    this.unhighlightTimeslots = function(timeslots) {
        /**
         * Removes a class from all non-disabled cells corresponding to each
         * timeslot in timeslots.
         *
         * @param timeslots: A 1-d array of tiemslot IDs
         * @param className: The class to remove from the cells
         */
        removeClassFromTimeslots = function(timeslots, className) {
            $j.each(timeslots, function(j, timeslot) {
                $j.each(this.rooms, function(k, room) {
                    var cell = this.getCell(room.id, timeslot);
                    cell.el.removeClass(className);
                }.bind(this));
            }.bind(this));
        }.bind(this);

        var available_timeslots = timeslots[0];
        var teaching_timeslots = timeslots[1];
        removeClassFromTimeslots(available_timeslots, "teacher-available-cell");
        removeClassFromTimeslots(teaching_timeslots, "teacher-teaching-cell");
    };


    /**
     * Initialize the sections that have already been scheduled. Must be called at the end 
     * after all other initialization happens.
     */
    this.initSections = function() {
        // Associated already scheduled classes with rooms
	    $j.each(this.sections.scheduleAssignments, function(class_id, assignmentData){
	        $j.each(assignmentData.timeslots, function(j, timeslot_id){
		        var cell = this.getCell(assignmentData.room_name, timeslot_id);
                if(cell && !cell.disabled) {
                    cell.addSection(sections.getById(class_id));
                } else {
                    if(!cell) {
                        var errorMessage = "Error: Could not find cell with room "
                            + assignmentData.room_name
                            + " and timeslot with id "
                            + timeslot_id
                            + " to schedule section with id "
                            + class_id;
                        console.log(errorMessage);
                        messagePanel.addMessage(errorMessage);
                    }
                    else {
                        var errorMessage = "Error: Room "
                            + assignmentData.room_name
                            + " appears to be unavailable during timeslot with id "
                            + timeslot_id
                            + " but section with id "
                            + class_id
                            + " is scheduled there.";
                        console.log(errorMessage);
                        messagePanel.addMessage(errorMessage);
                    }
                }
	        }.bind(this));
	    }.bind(this));
    };


    /**
     * Gets the cell that represents room_name and timeslot_id.
     * 
     * @param room_name: The name of the room corresponding to the cell
     * @param timeslot_id: The ID of the timeslot corresponding to the cell
     */
    this.getCell = function(room_name, timeslot_id){
	    return this.cells[room_name][this.timeslots.get_by_id(timeslot_id).order];
    };


    /**
     * Checks a section we want to schedule in room_name during schedule_timeslots
     * to make sure the room is available during that time and the length is nonzero.
     *
     * Returns an object with property valid that is set to whether the assignment is valid
     * and reason which contains a message if valid is false.
     *
     * @param section: The section to validate.
     * @param room_name: The name of the room we want to put the section into.
     * @param schedule_timeslots: The array of timeslots we want to put the section into.
     */
    this.validateAssignment = function(section, room_name, schedule_timeslots){
        var result = {
            valid: true,
            reason: null,
        }
        
        // Check to make sure there are timeslots
	    if (!schedule_timeslots){
            result.valid = false;
            result.reason = "Error: Not scheduled during a timeblock";
	        return result;
	    }

        // Check to make sure all the cells are unoccupied
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
     * Return the text of a room tooltip.
     * 
     * @param room: The room to get information about
     */
    this.tooltip = function(room) {
        var tooltip_parts = [
            "<b>" + room.text + "</b>",
            "Capacity: " + room.num_students + " students",
        ];
        return tooltip_parts.join("</br>");
    };

    /**
     * Render the matrix.
     */
    this.render = function(){
	    var table = $j("<table/>");

	    //Time headers
	    var header_row = $j("<tr/>").appendTo($j("<thead/>").appendTo(table));
	    $j("<th/>").appendTo(header_row);
	    $j.each(this.timeslots.timeslots, function(id, timeslot){
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
	        for(i = 0; i < Object.keys(this.timeslots.timeslots).length; i++){
		        cells[id][i].el.appendTo(row);
	        }
	    }.bind(this));
	    table.appendTo(this.el);
    };

    this.initSections();

};

