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
            show: {duration: 100},
            hide: {duration: 100},
            track: true,
	    });

        // If the cell is initialized with a section, add it.
	    if (new_section != null){
	        this.addSection(new_section);
	    }
        // Otherwise call removeSection to apply the correct styling
	    else{
	        this.removeSection();
	    }
	    this.el.addClass("matrix-cell");
    }


    /**
     * Highlight a cell and show its info in the section-info panel.
     */
    this.select = function() {
        if(this.el.hasClass("selectable-cell")) {
            this.el.addClass("selected-section");
        }
    };

    /**
     * Unhighlight a cell and hide the section-info panel.
     */
    this.unselect = function() {
        if(this.el.hasClass("selected-section")) {
            this.el.removeClass("selected-section");
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
            "Resource Requests:" + this.matrix.sections.getResourceString(this.section),
            "Flags: " + this.section.flags,
	    ];
        if(this.section.comments) {
            tooltip_parts.push("Comments: " + this.section.comments);
        }
        if(this.section.special_requests && this.section.special_requests.length > 0) {
            tooltip_parts.push("Room Requests: " + this.section.special_requests);
        }
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
        this.el.css("background-color", "");
    };

    /**
     * Add a section as a ghost.
     *
     * @param section: The section to display.
     */
    this.addGhostSection = function(section) {
        this.el.css("background", this.cellColors.color(section));
        this.el.css("color", this.cellColors.textColor(section));
        this.el.addClass("ghost-section");
        this.el[0].innerHTML = section.emailcode;
    };

    /**
     * Remove the ghost section and put back the original section if present.
     */
    this.removeGhostSection = function() {
        this.el.removeClass("ghost-section");
        this.el.css("background", "");
        if(this.section) {
            this.addSection(this.section);
        } else {
            this.removeSection();
        }
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
