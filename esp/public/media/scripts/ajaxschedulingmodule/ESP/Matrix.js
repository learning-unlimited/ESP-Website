function Matrix(
    timeslots,
    rooms,
    sections,
    el,
    messagePanel,
    sectionInfoPanel
){ 
    this.el = el;
    this.messagePanel = messagePanel;
    this.sectionInfoPanel = sectionInfoPanel;
    this.currently_selected = null;
    this.el.id = "matrix-table";

    this.rooms = rooms;

    this.sections = sections;
    this.sections.bindMatrix(this);

    this.timeslots = timeslots;

    this.init = function(){
        // set up cells
        var matrix = this;
        this.cells = function(){
            // cells has room names as keys and arrays of timeslots as values
	        var cells = {};
	        $j.each(rooms, function(room_name, room){
	            cells[room_name] = [];
	            i = 0;
	            $j.each(this.timeslots.timeslots, function(timeslot_id_string, timeslot){
		            var timeslot_id = parseInt(timeslot_id_string);
		            if (room.availability.indexOf(timeslot_id) >= 0){
		                cells[room_name][i] = new Cell($j("<td/>"), null, room_name, timeslot_id, matrix);
		            } else {
		                cells[room_name][i] = new DisabledCell($j("<td/>"))
		            }
		            i = i + 1;
	            });
	        }.bind(this));
            return cells;
        }.bind(this)();

        // set up handlers
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
        this.el.on("click", "td.teacher-available-cell", function(evt, ui) {
            var cell = $j(evt.currentTarget).data("cell");
            if(this.currently_selected) {
                this.sections.scheduleSection(this.currently_selected.section, cell.room_name, cell.timeslot_id);
                this.currently_selected.unselect();
            }
        }.bind(this));


    };

    this.init();
    
    this.initSections = function() {
        // Associated already scheduled classes with rooms
	    $j.each(this.sections.scheduleAssignments, function(class_id, assignmentData){
	        $j.each(assignmentData.timeslots, function(j, timeslot_id){
		        this.getCell(assignmentData.room_name, timeslot_id).addSection(sections.getById(class_id));
	        }.bind(this));
	    }.bind(this));
    };


    /**
     * Gets the cell that represents room_name and timeslot_id
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

