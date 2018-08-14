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
    this.timeslotHeaders = {};

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
                $j.each(this.timeslots.timeslots, function(timeslot_id_string, timeslot){
                    var timeslot_id = parseInt(timeslot_id_string);
                    if (room.availability.indexOf(timeslot_id) >= 0){
                        cells[room_name][timeslot.order] = new Cell($j("<td/>"), null, room_name,
                            timeslot_id, matrix);
                    } else {
                        cells[room_name][timeslot.order] = new DisabledCell($j("<td/>"), room_name,
                            timeslot_id)
                    }
                }.bind(this));
            }.bind(this));
            return cells;
        }.bind(this)();

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
    this.highlightTimeslots = function(timeslots, section) {
        /**
         * Adds a class to all non-disabled cells corresponding to each
         * timeslot in timeslots.
         *
         * @param timeslots: A 1-d array of tiemslot IDs
         * @param className: The class to add to the cells
         */
        addClassToTimeslots = function(timeslots, className) {
            $j.each(timeslots, function(j, timeslot) {
                this.timeslotHeaders[timeslot].addClass(className);
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
        if(section.length<=1) {
            return;
        }
        $j.each(available_timeslots, function(j, timeslot_id) {
            var timeslot = this.timeslots.get_by_id(timeslot_id);
            $j.each(this.rooms, function(k, room) {
                var cell = this.getCell(room.id, timeslot_id);
                if(cell.el.hasClass("teacher-available-cell")) {
                    var scheduleTimeslots = [timeslot.id];
                    var notEnoughSlots = false;
                    for(var i=1; i<section.length; i++) {
                        var nextTimeslot = this.timeslots.get_by_order(timeslot.order+i);
                        if(nextTimeslot) {
                            scheduleTimeslots.push(nextTimeslot.id);
                        } else {
                            notEnoughSlots = true;
                        }
                    }
                    if(notEnoughSlots ||
                       !this.validateAssignment(section, room.id, scheduleTimeslots).valid) {
                                cell.el.removeClass("teacher-available-cell");
                                cell.el.addClass("teacher-available-not-first-cell");
                    }
                }
            }.bind(this));
        }.bind(this));
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
                this.timeslotHeaders[timeslot].removeClass(className);
                $j.each(this.rooms, function(k, room) {
                    var cell = this.getCell(room.id, timeslot);
                    cell.el.removeClass(className);
                }.bind(this));
            }.bind(this));
        }.bind(this);

        var available_timeslots = timeslots[0];
        var teaching_timeslots = timeslots[1];
        removeClassFromTimeslots(available_timeslots, "teacher-available-cell teacher-available-not-first-cell");
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

        var availableTimeslots = this.sections.getAvailableTimeslots(section)[0];
        var validateIndividualCell = function(index, cell) {
            return !(cell.disabled || (cell.section && cell.section !== section) ||
                    availableTimeslots.indexOf(schedule_timeslots[index]) == -1);
        };

        var firstCell = this.getCell(room_name, schedule_timeslots[0]);
        if (section.length <= 1 && !validateIndividualCell(0, firstCell)) {
            result.valid = false;
            result.reason = "first cell is not valid"
            return result;
        }

        // Check to make sure all the cells are available
        for(var timeslot_index in schedule_timeslots){
            var cell = this.getCell(room_name, schedule_timeslots[timeslot_index]);
            if (!validateIndividualCell(timeslot_index, cell)){
                result.valid = false;
                result.reason = "Error: timeslot" +  schedule_timeslots[timeslot_index] +
                    " already has a class in " + room_name + "."
                return result;
            }
        }

        // Check to make sure all timeslots are contiguous.
        var timeslot_objects = schedule_timeslots.map(function(timeslot_id){return timeslots.get_by_id(timeslot_id);});
        if (!timeslots.are_timeslots_contiguous(timeslot_objects)){
            result.valid = false;
            result.reason = "Error: timeslots starting from " + schedule_timeslots[0] +
                " are not contiguous."
            return result;
        }

        // Check lunch constraints.
        var scheduled_over_lunch = false;
        $j.each(this.timeslots.lunch_timeslots, function(day, lunch_slots) {
            if(this.timeslots.on_same_day(lunch_slots[0], this.timeslots.get_by_id(schedule_timeslots[0]))) {
               var count = 0;
               $j.each(lunch_slots, function(index, lunch_slot) {
                    if(schedule_timeslots.indexOf(lunch_slot.id) > -1) {
                        count++;
                    }
                });
                if(count == lunch_slots.length) {
                    scheduled_over_lunch = true;
                }
            }
        }.bind(this));
        if(scheduled_over_lunch) {
            result.valid = false;
            result.reason = "scheduled over lunch";
            return result;
        }
        return result;
    };


    /**
     * Render the matrix.
     */
    this.render = function(){
        var table = $j("<table/>");
        var colModal = [{width: 140, align: "center"}];

        //Time headers
        var header_row = $j("<tr/>").appendTo($j("<thead/>").appendTo(table));
        header_row.append($j("<th/>"));
        $j.each(this.timeslots.timeslots_sorted, function(index, timeslot){
            var timeslotHeader = $j("<th>" + timeslot.label + "</th>");
            this.timeslotHeaders[timeslot.id] = timeslotHeader;
            timeslotHeader.appendTo(header_row);
            colModal.push({width: 80, align: 'center'});
        }.bind(this));
        //Room headers
        var rows = {}; //table rows by room name
        var room_ids = Object.keys(this.rooms);
        room_ids.sort(function (room1, room2) {
            // sort by building number
            var bldg1 = parseInt(room1, 10);
            var bldg2 = parseInt(room2, 10);
            if (!isNaN(bldg1) && !isNaN(bldg2) && bldg1 != bldg2) {
                return bldg1 - bldg2;
            }
            return room1.localeCompare(room2);
        });
        $j.each(this.rooms, function(id, room){
            room = this.rooms[id];
            var room_header = $j("<td>")
                .addClass('room')
                .text(id + " [" + room['num_students'] + "]")
                .attr('data-id', id);
            var row = $j("<tr></tr>");
            room_header.appendTo(row);
            rows[id] = row;
        }.bind(this));
        //populate cells
        var cells = this.cells;
        $j.each(room_ids, function(index, room_id){
            row = rows[room_id];
            for(i = 0; i < this.timeslots.timeslots_sorted.length; i++){
                cells[room_id][i].el.appendTo(row);
            }
            row.appendTo(table);
        }.bind(this));
        table.appendTo(this.el);
        table.fxdHdrCol({fixedCols: 1, colModal: colModal, width: "100%", height: "100%"});

        // Hack to make tooltips work
        var that = this;
        this.el.tooltip({
            content: function() {
                var room = that.rooms[$j(this).data('id')];
                var resource_lines = [];
                $j.each(room.resources, function(index, resource) {
                    var desc = resource.resource_type.name;
                    if(resource.value) {
                        desc += ': ' + resource.value;
                    }
                    resource_lines.push(desc);
                });
                var tooltipParts = [
                    "<b>" + room.text + "</b>",
                    "Capacity: " + room.num_students + " students",
                    "Resources: " + "<ul><li>"+ resource_lines.join("</li><li>") + "</li></ul>",
                ];
                return tooltipParts.join("</br>");
            },
            items: ".ft_c td",
            track: true,
            show: {duration: 100},
            hide: {duration: 100},
        });
    };


    this.initSections();

};
