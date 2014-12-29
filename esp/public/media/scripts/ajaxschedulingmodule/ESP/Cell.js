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

    this.dragHelper = function(){
	    var div = $j("<div/>");
	    var i;
	    for (i = 0; i < this.section.length; i++){
	        div.append(this.el.clone(false));
	    }
	    return div;
    }.bind(this);

    this.init = function(new_section){
	    this.el.data("cell", this);
	    this.el.draggable({
	        stack: ".matrix-cell",
	        helper: this.dragHelper,
	    });

	    this.el.droppable({
	        drop: function(ev, ui){
		        //handled by matrix
	        }
	    });

	    $j(this.el).tooltip({
	        items: ".occupied-cell",
	        content: this.tooltip.bind(this)
	    });

        this.el.on("dragstart", function(evt) {
            if(this.matrix.currently_selected) {
                this.matrix.currently_selected.unselect();
            }
            this.availableTimeslots = this.matrix.getAvailableTimeslotsForSection(this.section);
            this.highlightTimeslots(this.availableTimeslots);

        }.bind(this));

        this.el.on("dragstop", function(evt) {
            this.unhighlightTimeslots(this.availableTimeslots);
            this.availableTimeslots = [];
        }.bind(this));
        
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
            this.availableTimeslots = this.matrix.getAvailableTimeslotsForSection(this.section);
            this.highlightTimeslots(this.availableTimeslots);
            this.matrix.currently_selected = this;
            this.displayInfoOnPanel(this.matrix.section_info_el, this.matrix.message_el);
        }
    };

    this.unselect = function() {
        if(this.el.hasClass("selected-section")) {
            this.el.removeClass("selected-section");
            this.unhighlightTimeslots(this.availableTimeslots);
            this.matrix.currently_selected = null;
            this.hideInfoPanel(this.matrix.section_info_el, this.matrix.message_el);
        }
    };

    /**
     * Display info for a class and a toolbar. Optionally supply elementToReplace
     * parameter and replace elementToReplace with element.
     */

    this.displayInfoOnPanel = function(element, elementToReplace) {
        element.append("<div class='ui-widget-header'>Information for " + this.section.emailcode + "</div>")
        var contentDiv = $j("<div class='ui-widget-content'></div>");
        element.append(contentDiv);
        var unscheduleButton = $j("<button id='unschedule'>Unschedule Section</button></br>");
        unscheduleButton
            .button()
            .click(function(evt) {
                this.matrix.unscheduleSection(this.section.id);
            }.bind(this));
        contentDiv.append(unscheduleButton);

        // Make content
        var teacher_list = []
        $j.each(this.section.teachers, function(index, teacher_id) {
            var teacher = this.matrix.teachers[teacher_id]
            teacher_list.push(teacher.first_name + " " + teacher.last_name);
        }.bind(this));
        var teachers = teacher_list.join(", ");
        
        var content_parts = [
            "Title: " + this.section.title,
            "Teachers: " + teachers,
            "Class size max: " + this.section.class_size_max,
	        "Length: " + Math.ceil(this.section.length),
            "Grades: " + this.section.grade_min + "-" + this.section.grade_max,
        ]

        contentDiv.append(content_parts.join("</br>"));
        element.removeClass("ui-helper-hidden");
        if(elementToReplace) {
            elementToReplace.addClass("ui-helper-hidden");
        }
        
    };

    this.hideInfoPanel = function(element, elementToReplace) {
        element[0].innerHTML = "";
        element.addClass("ui-helper-hidden");
        if(elementToReplace) {
            elementToReplace.removeClass("ui-helper-hidden");
        }
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
	    this.el.droppable("enable");
	    this.el.draggable("disable");
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
	    this.el.droppable("disable");
	    this.el.draggable("enable");
    };

    /**
     * Create data for the tooltip
     */
    this.tooltip = function(){
        var teacher_list = []
        $j.each(this.section.teachers, function(index, teacher_id) {
            var teacher = this.matrix.teachers[teacher_id]
            teacher_list.push(teacher.first_name + " " + teacher.last_name);
        }.bind(this));
        var teachers = teacher_list.join(", ");
	    var tooltip_parts = [
	        "<b>" + this.section.emailcode + ": " + this.section.title + "</b>", 
            "Teachers: " + teachers,
	        "Class size max: " + this.section.class_size_max,
	        "Length: " + Math.ceil(this.section.length),
            "Grades: " + this.section.grade_min + "-" + this.section.grade_max,
	    ];
	    return tooltip_parts.join("<br/>");
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
