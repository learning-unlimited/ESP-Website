/**
 * The grid of cells (Cells) that displays the schedule.
 * Has pointers to Sections, Timeslots, and the rooms data
 *
 * @param timeslots: A Timeslots object corresponding to times available for classes
 * @param rooms: The rooms that are available for scheduling. Keys are ids values are room data.
 * @param sections: A list of all sections for the program
 * @param el: The element to morph into the matrix
 * @param messsagePanel: The panel that can display messages and errors
 * @param sectionInfoPanel: The panel that displays section info
 * @param moderatorDirectory: The interface for moderator scheduling
 */
function Matrix(
        timeslots,
        rooms,
        categories,
        sections,
        el,
        messagePanel,
        sectionInfoPanel,
        moderatorDirectory
        ){
    this.el = el;
    this.el.id = "matrix-table";

    this.timeslots = timeslots;
    this.categories = categories;
    this.rooms = rooms;
    
    // Set up filtering
    this.filter = {
        roomCapacityMin: {active: false, el: $j("input#room-filter-capacity-min"), type: "number"},
        roomCapacityMax: {active: false, el: $j("input#room-filter-capacity-max"), type: "number"},
        roomResource: {active: false, el: $j("input#room-filter-resource-text"), type: "string"},
        roomName: {active: false, el: $j("input#room-filter-name-text"), type: "string"},
    };
    this.filter.roomCapacityMin.valid = function(a) {
        return a.num_students >= this.filter.roomCapacityMin.val;
    }.bind(this);
    this.filter.roomCapacityMax.valid = function(a) {
        return a.num_students <= this.filter.roomCapacityMax.val;
    }.bind(this);
    this.filter.roomResource.valid = function(a) {
        var result = false;
        $j.each(a.resource_lines, function(index, resource) {
            if((resource).toLowerCase().search(this.filter.roomResource.val)>-1) {
                result = true;
            }
        }.bind(this));
        return result;
    }.bind(this);
    this.filter.roomName.valid = function(a) {
        return (a.text).toLowerCase().search(this.filter.roomName.val)>-1
    }.bind(this);

    $j.each(this.filter, function(filterName, filterObject) {
        filterObject.el.on("change", function() {
            filterObject.val = filterObject.el.val().trim();
            if(filterObject.type==="number") {
                filterObject.val = parseInt(filterObject.val);
            } else if(filterObject.type==="string") {
                filterObject.val = filterObject.val.toLowerCase()
            } else if(filterObject.type==="boolean") {
                filterObject.val = filterObject.el.prop('checked');
            }
            if((filterObject.type==="number" && isNaN(filterObject.val))
                || (filterObject.type==="string" && filterObject.val.trim()==="")
                || (filterObject.type==="boolean" && !filterObject.val)) {
                filterObject.active = false;
            } else {
                filterObject.active = true;
            }
            $j("body").trigger("room-filters-changed");
        });
    }.bind(this));
    
    /**
     * Get the rooms satisfying the search criteria.
     */
    this.filteredRooms = function(){
        var returnedRooms = [];
        $j.each(this.rooms, function(index, room) {
            var roomValid;
            // check every criterion in the room filter tab, short-circuiting if possible
            roomValid = true;
            for (var filterName in this.filter) {
                if (this.filter.hasOwnProperty(filterName)) {
                    var filterObject = this.filter[filterName];
                    // this loops over properties in this.filter
                    if (filterObject.active && !filterObject.valid(room)) {
                        roomValid = false;
                        break;
                    }
                }
            }
            if (roomValid) {
                returnedRooms.push(room);
            }
        }.bind(this));
        return returnedRooms;
    };
    
    this.updateRooms = function(){
        var filtRooms = this.filteredRooms()
        $j.each(this.rooms, function(index, room) {
            // get rows to show or hide
            var rows = $j(".room[data-id='" + room.id + "']").parent();
            if (filtRooms.includes(room)) {
                rows.css("display", "table-row");
            } else {
                rows.css("display", "none");
            }
        }.bind(this));
    };

    this.sections = sections;
    this.sections.bindMatrix(this);
    this.moderatorDirectory = moderatorDirectory;
    if(has_moderator_module === "True") this.moderatorDirectory.bindMatrix(this);

    /**
     * Bind a scheduler to the matrix to access various functions
     *
     * @param scheduler: The scheduler to bind
     */
    this.bindScheduler = function(scheduler) {
        this.scheduler = scheduler;
    }

    // Set up scheduling checks
    this.updateCells = function(){
        $j.each(this.cells, function(index, room) {
            $j.each(room, function(index, cell) {
                if(!cell.disabled && cell.section) cell.update();
            })
        });
    };
    
    this.scheduling_check = "";
    $j('input[type=radio][name=scheduling-checks]').on("change", function() {
        this.scheduling_check = event.target.value;
        this.updateCells();
    }.bind(this));

    this.messagePanel = messagePanel;
    this.sectionInfoPanel = sectionInfoPanel;
    this.timeslotHeaders = {};

    /**
     * Initialize the matrix
     */
    this.init = function(){
        $j("body").on("room-filters-changed", this.updateRooms.bind(this));
        // set up cells
        var matrix = this;
        this.cells = function(){
            // cells has room ids as keys to the outer object and timeslots as keys to the
            // inner object
            var cells = {};
            $j.each(rooms, function(room_id, room){
                cells[room_id] = [];
                $j.each(this.timeslots.timeslots, function(timeslot_id_string, timeslot){
                    var timeslot_id = parseInt(timeslot_id_string);
                    if (room.availability.indexOf(timeslot_id) >= 0){
                        cells[room_id][timeslot.order] = new Cell($j("<td/>"), null, room_id,
                            timeslot_id, matrix);
                    } else {
                        cells[room_id][timeslot.order] = new DisabledCell($j("<td/>"), room_id,
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
     * @param moderator: An optional moderator (if specified, shows moderator availability)
     */
    this.highlightTimeslots = function(timeslots, section, moderator = null) {
        /**
         * Adds a class to all non-disabled cells corresponding to each
         * timeslot in timeslots.
         *
         * @param timeslots: A 1-d array of timeslot IDs
         * @param className: The class to add to the cells
         * @param moderator: An optional moderator (if specified, adds class to section cells)
         */
        addClassToTimeslots = function(timeslots, className, moderator = null) {
            $j.each(timeslots, function(j, timeslot) {
                this.timeslotHeaders[timeslot].addClass(className);
                $j.each(this.rooms, function(k, room) {
                    var cell = this.getCell(room.id, timeslot);
                    if(moderator){ // If we are doing moderator availability, we want to highlight cells with sections
                        if(cell.section && !cell.section.moderators.includes(moderator.id)) {
                            cell.el.addClass(className);
                        }
                    } else if(!cell.section && !cell.disabled) { // If we're doing class availability, we want to highlight cells without sections
                        cell.el.addClass(className);
                    }
                }.bind(this));
            }.bind(this));
        }.bind(this);
        /**
         * Adds a class to all non-disabled cells corresponding to each
         * section in sections.
         *
         * @param sections: A 1-d array of section IDs
         * @param className: The class to add to the cells
         */
        addClassToSections = function(sections, className) {
            $j.each(sections, function(j, section) {
                var assignment = this.sections.scheduleAssignments[section];
                if(assignment.room_id) {
                    var roomID = assignment.room_id;
                    $j.each(assignment.timeslots, function(k, timeslot) {
                        var cell = this.getCell(roomID, timeslot);
                        if(!cell.disabled) {
                            cell.el.addClass(className);
                        }
                    }.bind(this));
                }
            }.bind(this));
        }.bind(this);
        var available_timeslots = timeslots[0];
        var teaching_timeslots = timeslots[1];
        if(moderator){
            addClassToTimeslots(available_timeslots, "moderator-available-cell", moderator);
            addClassToTimeslots(teaching_timeslots, "moderator-teaching-cell", moderator);
            var not_first_sections = [];
            var not_available_sections = []
            for(var sec in this.sections.scheduleAssignments) {
                for(var timeslot of this.sections.scheduleAssignments[sec].timeslots) {
                    if(teaching_timeslots.includes(timeslot) && !(not_first_sections.includes(sec))){
                        not_first_sections.push(sec);
                    }
                    if(!(available_timeslots.includes(timeslot) || teaching_timeslots.includes(timeslot)) && !(not_available_sections.includes(sec))){
                        not_available_sections.push(sec);
                    }
                }
            }
            addClassToSections(not_first_sections, "moderator-available-not-first-cell");
            addClassToSections(not_available_sections, "moderator-unavailable-cell");
            addClassToSections(Object.keys(this.sections.scheduleAssignments).filter(section => this.sections.sections_data[section].moderators.length > 0), "lowOpacity");
            addClassToTimeslots(Object.values(this.timeslots.timeslots).map(el => el.id).filter(el => !(available_timeslots.includes(el) || teaching_timeslots.includes(el))), "moderator-unavailable-cell", moderator);
            addClassToSections(this.moderatorDirectory.getTeachingAndModeratingSections(moderator), "moderator-moderating-or-teaching-cell");
            if($j("#mod-category-match").prop("checked")) {
                addClassToSections(Object.keys(this.sections.scheduleAssignments).filter(section => !(moderator.categories.includes(this.sections.sections_data[section].category_id))), "hiddenCell")
            }
            addClassToSections(moderator.sections, "moderator-is-moderating-this-cell");
        } else {
            addClassToTimeslots(available_timeslots, "teacher-available-cell");
            addClassToTimeslots(teaching_timeslots, "teacher-teaching-cell");
        }
        
        if(section){
            $j.each(available_timeslots, function(j, timeslot_id) {
                $j.each(this.rooms, function(k, room) {
                    var cell = this.getCell(room.id, timeslot_id);
                    if(cell.el.hasClass("teacher-available-cell")) {
                        var scheduleTimeslots = this.timeslots.get_timeslots_to_schedule_section(section, timeslot_id);
                        if(scheduleTimeslots == null || !this.validateAssignment(section, room.id, scheduleTimeslots).valid) {
                            cell.el.removeClass("teacher-available-cell");
                            cell.el.addClass("teacher-available-not-first-cell");
                        }
                    }
                }.bind(this));
            }.bind(this));
            for(var teacher of section.teacher_data) {
                addClassToSections(_.difference(teacher.sections, [section.id]), "teacher-is-teaching-this-cell");
            }
        }
    }

    /**
     * Unhighlight the cells that are currently highlighted
     *
     * @param timeslots: A 2-d array. The first element is an array of
     *                   timeslots where all teachers are completely available.
     *                   The second is an array of timeslots where one or more
     *                   teachers are teaching, but would be available otherwise.
     * @param moderator: An optional moderator (if specified, removes moderator availability)
     */
    this.unhighlightTimeslots = function(timeslots, moderator = null) {
        /**
         * Removes a class from all non-disabled cells corresponding to each
         * timeslot in timeslots.
         *
         * @param timeslots: A 1-d array of timeslot IDs
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
        /**
         * Removes a class from all non-disabled cells corresponding to each
         * section in sections.
         *
         * @param sections: A 1-d array of section IDs
         * @param className: The class to remove from the cells
         */
        removeClassFromSections = function(sections, className) {
            $j.each(sections, function(j, section) {
                var assignment = this.sections.scheduleAssignments[section];
                if(assignment.room_id) {
                    var roomID = assignment.room_id;
                    $j.each(assignment.timeslots, function(k, timeslot) {
                        var cell = this.getCell(roomID, timeslot);
                        if(!cell.disabled) {
                            cell.el.removeClass(className);
                        }
                    }.bind(this));
                }
            }.bind(this));
        }.bind(this);

        var available_timeslots = timeslots[0];
        var teaching_timeslots = timeslots[1];
        if(moderator) {
            removeClassFromTimeslots(available_timeslots, "moderator-available-cell");
            removeClassFromTimeslots(teaching_timeslots, "moderator-teaching-cell");
            removeClassFromTimeslots(Object.values(this.timeslots.timeslots).map(el => el.id).filter(el => !(available_timeslots.includes(el) || teaching_timeslots.includes(el))), "moderator-unavailable-cell");
            removeClassFromSections(Object.keys(this.sections.scheduleAssignments), "moderator-is-moderating-this-cell moderator-teaching-cell moderator-unavailable-cell moderator-available-cell moderator-moderating-or-teaching-cell moderator-available-not-first-cell lowOpacity hiddenCell");
        } else {
            removeClassFromTimeslots(available_timeslots, "teacher-available-cell teacher-available-not-first-cell");
            removeClassFromTimeslots(teaching_timeslots, "teacher-teaching-cell");
            removeClassFromSections(Object.keys(this.sections.scheduleAssignments), "teacher-is-teaching-this-cell");
        }
    };


    /**
     * Initialize the sections that have already been scheduled. Must be called at the end
     * after all other initialization happens.
     */
    this.initSections = function() {
        // Associated already scheduled classes with rooms
        $j.each(this.sections.scheduleAssignments, function(class_id, assignmentData){
            if(assignmentData.room_id){
                $j.each(assignmentData.timeslots, function(j, timeslot_id){
                    var cell = this.getCell(assignmentData.room_id, timeslot_id);
                    if(cell && !cell.disabled) {
                        cell.addSection(sections.getById(class_id));
                    } else {
                        if(!cell) {
                            var errorMessage = "Error: Could not find cell with room with id "
                                + assignmentData.room_id
                                + " and timeslot with id "
                                + timeslot_id
                                + " to schedule section with id "
                                + class_id;
                            console.log(errorMessage);
                            messagePanel.addMessage(errorMessage);
                        }
                        else {
                            var errorMessage = "Error: Room with id "
                                + assignmentData.room_id
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
            }
        }.bind(this));
    };


    /**
     * Gets the cell that represents room_id and timeslot_id.
     *
     * @param room_id: The id of the room corresponding to the cell
     * @param timeslot_id: The ID of the timeslot corresponding to the cell
     */
    this.getCell = function(room_id, timeslot_id){
        return this.cells[room_id][this.timeslots.get_by_id(timeslot_id).order];
    };


    /**
     * Checks a section we want to schedule in room_id during schedule_timeslots
     * to make sure the room is available during that time and the length is nonzero.
     *
     * Returns an object with property valid that is set to whether the assignment is valid
     * and reason which contains a message if valid is false.
     *
     * @param section: The section to validate.
     * @param room_id: The name of the room we want to put the section into.
     * @param schedule_timeslots: The array of timeslots we want to put the section into.
     * @param ignore_sections: An optional array of sections to ignore
     */
    this.validateAssignment = function(section, room_id, schedule_timeslots, ignore_sections = []){
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

        var availableTimeslots = this.sections.getAvailableTimeslots(section, ignore_sections)[0];
        var validateIndividualCell = function(index, cell) {
            if(cell.disabled){
                return "Error: " + this.rooms[cell.room_id].text + " is not available during timeslot " + (this.timeslots.get_by_id(cell.timeslot_id).order + 1).toString();
            } else if (cell.section && cell.section !== section && !ignore_sections.includes(cell.section)) {
                return "Error: There is already a class scheduled in " + this.rooms[cell.room_id].text + " during timeslot " + (this.timeslots.get_by_id(cell.timeslot_id).order + 1).toString();
            } else if (availableTimeslots.indexOf(schedule_timeslots[index]) == -1){
                return "Error: The teachers of " + section.emailcode + " are not available during timeslot " + (this.timeslots.get_by_id(cell.timeslot_id).order + 1).toString();
            } else {
                return true;
            }
        }.bind(this);

        // Check to make sure all the cells are available
        for(var timeslot_index in schedule_timeslots){
            var cell = this.getCell(room_id, schedule_timeslots[timeslot_index]);
            var valid = validateIndividualCell(timeslot_index, cell);
            if (valid != true){
                result.valid = false;
                result.reason = valid;
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
        var tbody = $j("<tbody/>");
        var colModal = [{width: 140, align: "center"}];

        //Time headers
        var header_row = $j("<tr/>").appendTo($j("<thead/>").appendTo(table));
        var header_corner = $j("<th/>").append($j("<button id = 'print_button'>Print Matrix</button>"));
        header_corner.append($j("<button id = 'legend_button'>Show Legend</button>"));
        header_row.append(header_corner);
        $j.each(this.timeslots.timeslots_sorted, function(index, timeslot){
            var timeslotHeader = $j("<th>" + timeslot.label + "</th>");
            this.timeslotHeaders[timeslot.id] = timeslotHeader;
            timeslotHeader.appendTo(header_row);
            colModal.push({width: 80, align: 'center'});
        }.bind(this));
        //Room headers
        var rows = {}; //table rows by room name
        var room_ids = Object.keys(this.rooms);
        room_ids = room_ids.sort(function (room1, room2) {
            // sort by building number
            return rooms[room1].text.localeCompare(rooms[room2].text, undefined, {
                numeric: true,
                sensitivity: 'base'
            })
        });
        $j.each(this.rooms, function(id, room){
            room = this.rooms[id];
            var room_header = $j("<td>")
                .addClass('room')
                .text(room.text + " [" + room['num_students'] + "]")
                .attr('data-id', id)
                .css({"max-width": "140px", "min-width": "140px"});
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
            row.appendTo(tbody);
        }.bind(this));
        tbody.appendTo(table);
        table.appendTo(this.el);
        table.fxdHdrCol({fixedCols: 1, colModal: colModal, width: "100%", height: "100%"});

        // Get both sets of headers
        $j.each(this.timeslots.timeslots_sorted, function(index, timeslot){
            var timeslotHeader = $j("th:contains('" + timeslot.label + "')");
            this.timeslotHeaders[timeslot.id] = timeslotHeader;
        }.bind(this));

        // Hack to make tooltips work
        var that = this;
        this.el.tooltip({
            content: function() {
                var room = that.rooms[$j(this).data('id')];
                var tooltipParts = [
                    "<b>" + room.text + "</b>",
                    "Capacity: " + room.num_students + " students",
                    "Resources: " + ((room.resource_lines.length > 0) ? "<ul><li>"+ room.resource_lines.join("</li><li>") + "</li></ul>" : "None"),
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
