/**
 * This is a cell that can have class sections assigned to it.
 */
function Cell(el, section, room_name, timeslot_id) {
    this.el = el;

    this.cellColors = new CellColors();
    this.room_name = room_name;
    this.timeslot_id = timeslot_id;
    this.disabled = false; // for tests

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
	    })
        
	    if (new_section != null){
	        this.addSection(new_section);
	    }
	    else{
	        this.removeSection();
	    }
	    this.el.addClass("matrix-cell");
    }

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
    };

    /**
     * Add a section to the cell and update associated data
     */
    this.addSection = function(section){
	    this.section = section;
	    this.el.data("section", section);
	    this.el.addClass("occupied-cell");
	    this.el.removeClass("available-cell");
	    this.el.css("background-color", this.cellColors.color(section));
        this.el.css("color", this.cellColors.textColor(section));
	    this.el[0].innerHTML = section.emailcode;
	    this.el.droppable("disable");
	    this.el.draggable("enable");
    };

    /**
     * Create data for the tooltip
     */
    this.tooltip = function(){
	    tooltip_parts = [
	        "Code: " + this.section.emailcode,
	        "Title: " + this.section.title,
	        "Class size max: " + this.section.class_size_max,
	        "Length: " + Math.ceil(this.section.length)
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
