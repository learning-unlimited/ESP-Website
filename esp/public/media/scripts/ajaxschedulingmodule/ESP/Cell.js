/**
 * This is a cell that can have class sections assigned to it.
 */
function Cell(el, section, room_name, timeslot_id, matrix) {
    this.el = el;

    this.cellColors = new CellColors();
    this.room_name = room_name;
    this.timeslot_id = timeslot_id;
    this.matrix = matrix;
    this.disabled = false; // for tests
    
    this.availableTimeslots = [];

    this.init = function(new_section){
	    this.el.data("cell", this);

	    $j(this.el).tooltip({
	        items: ".occupied-cell",
	        content: this.tooltip.bind(this),
	    });

	    if (new_section != null){
	        this.addSection(new_section);
	    }
	    else{
	        this.removeSection();
	    }
	    this.el.addClass("matrix-cell");
    }

    /**
     * Highlight the timeslots on the grid.
     *
     * Takes in timeslots which is an array. The first element is an array of
     * timeslots where all teachers are completely available. The second is an 
     * array of timeslots where one or more teachers are teaching, but would be
     * available otherwise.
     */
    this.highlightTimeslots = function(timeslots) {
        /**
         * Adds a class to all rooms with non-disabled cells in each
         * timeslot in timeslots.
         */
        addClassToTimeslots = function(timeslots, className) {
            $j.each(timeslots, function(j, timeslot) {
                $j.each(this.matrix.rooms, function(k, room) {
                    var cell = this.matrix.getCell(room.id, timeslot);
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
     */
    this.unhighlightTimeslots = function(timeslots) {
        removeClassFromTimeslots = function(timeslots, className) {
            $j.each(timeslots, function(j, timeslot) {
                $j.each(this.matrix.rooms, function(k, room) {
                    var cell = this.matrix.getCell(room.id, timeslot);
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
     * Highlight a cell and show its info in the section-info panel.
     */
    this.select = function() {
        if(this.el.hasClass("selectable-cell")) {
            this.el.addClass("selected-section");
            this.availableTimeslots = this.matrix.sections.getAvailableTimeslots(this.section);
            this.highlightTimeslots(this.availableTimeslots);
            this.matrix.currently_selected = this;
            this.matrix.sectionInfoPanel.displaySection(this.section);
        }
    };

    this.unselect = function() {
        if(this.el.hasClass("selected-section")) {
            this.el.removeClass("selected-section");
            this.unhighlightTimeslots(this.availableTimeslots);
            this.matrix.currently_selected = null;
            this.matrix.sectionInfoPanel.hide();
        }
    };

    /**
     * Create data for the tooltip
     */
    this.tooltip = function(){
	    var tooltip_parts = [
	        "<b>" + this.section.emailcode + ": " + this.section.title + "</b>", 
            "Teachers: " + this.matrix.sections.getTeachersString(this.section),
	        "Class size max: " + this.section.class_size_max,
	        "Length: " + Math.ceil(this.section.length),
            "Grades: " + this.section.grade_min + "-" + this.section.grade_max,
	    ];
	    return tooltip_parts.join("<br/>");
    };

    /**
     * Remove a section from the cell and all associated data
     */
    this.removeSection = function(){
	    this.section = null;
	    this.el.removeData("section");
	    this.el[0].innerHTML = "";
	    this.el.addClass("available-cell");
	    this.el.css("background-color", "#222222");
	    this.el.removeClass("occupied-cell");
        this.el.removeClass("selectable-cell");
    };

    /**
     * Add a section to the cell and update associated data
     */
    this.addSection = function(section){
	    this.section = section;
	    this.el.data("section", section);
	    this.el.addClass("occupied-cell");
        this.el.addClass("selectable-cell");
	    this.el.removeClass("available-cell");
	    this.el.css("background-color", this.cellColors.color(section));
        this.el.css("color", this.cellColors.textColor(section));
	    this.el[0].innerHTML = "<a href='#'>" + section.emailcode + "</a>";
    };

    this.hasSection = function(){
	    return this.section != null;
    };

    this.init(section);
}

/**
 * This is a cell where a room is not available in that time block.
 */
function DisabledCell(el) {
    this.el = el;
    this.disabled = true;
    this.init = function(new_section){
	    this.el.addClass("matrix-cell");
	    this.el.addClass("disabled-cell");
    };

    this.init();
}
