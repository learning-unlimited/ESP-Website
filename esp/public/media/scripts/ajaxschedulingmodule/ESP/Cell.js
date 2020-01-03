/**
 * This is a cell that can have class sections assigned to it.
 *
 * @param el: The jquery element that this cell should be rendered on.
 * @param section: The section that should be rendered on this cell (may be null).
 * @param room_id: The ID of the room that corresponds to this cell.
 * @param timeslot_id: The ID of the timeslot that corresponds to this cell.
 * @param matrix: The matrix that created the cell.
 *
 * Public properties and methods:
 * @prop el:
 * @prop cellColors
 * @prop room_id
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
function Cell(el, section, room_id, timeslot_id, matrix) {
    this.el = el;

    this.cellColors = new CellColors();
    this.room_id = room_id;
    this.timeslot_id = timeslot_id;
    this.matrix = matrix;
    this.disabled = false;

    this.section = null;
    this.ghostSection = false;
    this.selected = false;


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
     * Re-apply styling on the cell based on section/selected status.
     */
    this.update = function() {
        this.el.removeData("section");
        this.el.removeClass("available-cell occupied-cell selectable-cell locked-cell selected-section ghost-section");
        this.el[0].innerHTML = "";
        this.el.css("background-color", "");
        this.el.css("background", "");
        this.el.css("color", "");

        if(this.ghostSection || !this.section) {
            this.el.addClass("available-cell");

            if(this.ghostSection) {
                this.el.css("background", this.cellColors.background(this.ghostSection));
                this.el.css("color", this.cellColors.textColor(this.ghostSection));
                this.el.addClass("ghost-section");
                this.el[0].innerHTML = this.ghostSection.emailcode;
            }
        } else {
            this.el.data("section", this.section);
            this.el.addClass("occupied-cell");
            this.el.addClass("selectable-cell");
            if(this.section.schedulingLocked) {
                this.el.addClass("locked-cell");
            }
            if(this.selected) {
                this.el.addClass("selected-section");
            }
            this.el.css("background", this.cellColors.background(this.section));
            this.el.css("color", this.cellColors.textColor(this.section));
            this.el.css("background-size", "cover");
            this.el[0].innerHTML = "<a href='#'>" + this.section.emailcode + "</a>";
        }
    };

    /**
     * Highlight a cell and show its info in the section-info panel.
     */
    this.select = function() {
        this.selected = true;
        this.update();
    };

    /**
     * Unhighlight a cell and hide the section-info panel.
     */
    this.unselect = function() {
        this.selected = false;
        this.update();
    };

    /**
     * Create data for the tooltip
     *
     * Note: This has to be bound to the cell for the tooltip jquery function to
     *       work. It would be nice if this was in Sectinos instead.
     */
    this.tooltip = function(){
        var tooltip_parts = {};
        if(this.section.schedulingComment) {
            tooltip_parts['Scheduling Comment'] = this.section.schedulingComment +
                (this.section.schedulingLocked ? ' <b><i>(locked)</i></b>' : '');
        }
        tooltip_parts['Teachers'] = this.matrix.sections.getTeachersString(this.section);
        tooltip_parts['Class size max'] = this.section.class_size_max;
        tooltip_parts['Length'] = Math.ceil(this.section.length);
        tooltip_parts['Grades'] = this.section.grade_min + "-" + this.section.grade_max;
        tooltip_parts['Room Request'] = this.section.requested_room;
        tooltip_parts['Resource Requests'] = this.matrix.sections.getResourceString(this.section);
        tooltip_parts['Flags'] = this.section.flags;
        if(this.section.comments) {
            tooltip_parts['Comments'] = this.section.comments;
        }
        if(this.section.special_requests && this.section.special_requests.length > 0) {
            tooltip_parts['Room Requests'] = this.section.special_requests;
        }

        var tooltipText = "<b>" + this.section.emailcode + ": " + this.section.title + "</b>";
        for(var header in tooltip_parts) {
            tooltipText += "<br/><b>" + header + "</b>: " + tooltip_parts[header];
        }
        return tooltipText;
    };

    /**
     * Add a section to the cell and update associated data
     *
     * @param section: The section to add to the cell.
     */
    this.addSection = function(section){
        this.section = section;
        this.ghostSection = null;
        this.update();
    };

    /**
     * Remove a section from the cell and all associated data
     */
    this.removeSection = function(){
        this.section = null;
        this.update();
    };

    /**
     * Add a section as a ghost.
     *
     * @param section: The section to display.
     */
    this.addGhostSection = function(section) {
        this.ghostSection = section;
        this.update();
    };

    /**
     * Remove the ghost section and put back the original section if present.
     */
    this.removeGhostSection = function() {
        this.ghostSection = null;
        this.update();
    };


    this.init(section);
}

/**
 * This is a cell where a room is not available in that time block.
 */
function DisabledCell(el, room_id, timeslot_id) {
    this.room_id = room_id;
    this.timeslot_id = timeslot_id;
    this.el = el;
    this.disabled = true;
    this.init = function(new_section){
        this.el.addClass("matrix-cell");
        this.el.addClass("disabled-cell");
    };

    this.init();
}
