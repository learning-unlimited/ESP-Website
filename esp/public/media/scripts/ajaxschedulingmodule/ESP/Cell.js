/**
 * This is a cell that can have class sections assigned to it.
 *
 * @param el: The jquery element that this cell should be rendered on.
 * @param section: The section that should be rendered on this cell (may be null).
 * @param room_name: The name (ID) of the room that corresponds to this cell.
 * @param timeslot_id: The ID of the timeslot that corresponds to this cell.
 * @param matrix: The matrix that created the cell.
 *
 * Public properties and methods:
 * @prop el:
 * @prop cellColors
 * @prop room_name
 * @prop timeslot_id
 * @prop matrix
 * @prop disabled
 * @prop availableTimeslots: The timeslots that should be highlighted for the selected cell.
 *                           //TODO: Move availableTimeslots to Sections
 *
 * @method highlightTimeslots(timeslots)
 * @method unhighlightTimeslots(timeslots)
 * @method select()
 * @method unselect()
 * @method addSection(section)
 * @method removeSection()
 */
function Cell(el, section, room_name, timeslot_id, matrix) {
    this.el = el;

    this.cellColors = new CellColors();
    this.room_name = room_name;
    this.timeslot_id = timeslot_id;
    this.matrix = matrix;
    this.disabled = false;
    
    this.availableTimeslots = [];

    /**
     * Initialize the cell
     *
     * @param new_section: The section that the cell should be initialized with.
     *                     May be null.
     */
    this.init = function(new_section){
        // Add the cell as data to the element
	    this.el.data("cell", this);

        // When cells are occupied, show a tooltip
	    $j(this.el).tooltip({
	        items: ".occupied-cell",
	        content: this.tooltip.bind(this),
	    });

        // If the cell is initialized with a section, add it.
	    if (new_section != null){
	        this.addSection(new_section);
	    }
        // Otherwise call removeSection to apply the corret styling
	    else{
	        this.removeSection();
	    }
	    this.el.addClass("matrix-cell");
    }

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
     *
     * @param timeslots: A 2-d array. The first element is an array of
     *                   timeslots where all teachers are completely available. 
     *                   The second is an array of timeslots where one or more 
     *                   teachers are teaching, but would be available otherwise.
     */
    //TODO: Move this to Matrix.js
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
            this.matrix.sections.currentlySelected = this;
            this.matrix.sectionInfoPanel.displaySection(this.section);
        }
    };

    /**
     * Unhighlight a cell and hide the section-info panel.
     */
    this.unselect = function() {
        if(this.el.hasClass("selected-section")) {
            this.el.removeClass("selected-section");
            this.unhighlightTimeslots(this.availableTimeslots);
            this.matrix.sections.currentlySelected = null;
            this.matrix.sectionInfoPanel.hide();
        }
    };

    /**
     * Create data for the tooltip
     *
     * Note: This has to be bound to the cell for the tooltip jquery function to
     *       work. It would be nice if this was in Sectinos instead.
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
     * Add a section to the cell and update associated data
     *
     * @param section: The section to add to the cell.
     */
    this.addSection = function(section){
        // Add the section data
	    this.section = section;
	    this.el.data("section", section);

        // Mark the cell as occupied and selectable
	    this.el.addClass("occupied-cell");
        this.el.addClass("selectable-cell");
	    this.el.removeClass("available-cell");

        // Add the styling for the section
	    this.el.css("background-color", this.cellColors.color(section));
        this.el.css("color", this.cellColors.textColor(section));
	    this.el[0].innerHTML = "<a href='#'>" + section.emailcode + "</a>";
    };

    /**
     * Remove a section from the cell and all associated data
     */
    this.removeSection = function(){
        // Remove the section data
	    this.section = null;
	    this.el.removeData("section");

        // Mark the cell as available and unselectable
	    this.el.addClass("available-cell");
	    this.el.removeClass("occupied-cell");
        this.el.removeClass("selectable-cell");
        
        // Remove the styling for the section
	    this.el[0].innerHTML = "";
	    this.el.css("background-color", "#222222");

    };


    this.init(section);
}

/**
 * This is a cell where a room is not available in that time block.
 */
function DisabledCell(el, room_name, timeslot_id) {
    this.room_name = room_name;
    this.timeslot_id = timeslot_id;
    this.el = el;
    this.disabled = true;
    this.init = function(new_section){
	    this.el.addClass("matrix-cell");
	    this.el.addClass("disabled-cell");
    };

    this.init();
}
