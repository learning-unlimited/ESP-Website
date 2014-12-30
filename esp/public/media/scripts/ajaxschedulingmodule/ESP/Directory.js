/**
 * This is the directory of classes that has yet to be scheduled
 */
function Directory(sections, el, schedule_assignments, matrix) {
    this.sections = sections;
    this.el = el;
    this.schedule_assignments = schedule_assignments;
    this.matrix = matrix;

    this.render = function(){
        
        // Remove old classes from the directory
	    var oldChildren = this.el.children();
	    $j.each(oldChildren, function(c){
	        oldChildren[c].hidden = true;
	    });

	    setTimeout(function(){
	        $j.each(oldChildren, function(c){
		        oldChildren[c].remove();
	        });
	    }.bind(this), 0);

        // Create the directory table
	    var table = $j("<table/>");
	    $j.each(this.sections.filtered_sections(), function(id, section){
	        var row = new TableRow(section, $j("<tr/>"), this);
	        row.render();
	        row.el.appendTo(table);
	    }.bind(this))
	        table.appendTo(this.el);

    };

    this.init = function(){
        // set up handlers
        this.el.on("click", "td > a", function(evt, ui) {
            var cell = $j(evt.currentTarget.parentElement).data("cell");
            if(this.sections.currentlySelected === cell) {
                cell.unselect();
            } else {
                if(this.sections.currentlySelected) {
                    this.sections.currentlySelected.unselect();
                }
                cell.select();
            }
            
            
        }.bind(this)); 

        this.el.on("click", "td.teacher-available-cell", function(evt, ui) {
            var cell = $j(evt.currentTarget).data("cell");
            if(this.sections.currentlySelected) {
                this.sections.scheduleSection(this.sections.currentlySelected.section, cell.room_name, cell.timeslot_id);
                this.sections.currentlySelected.unselect();
            }
        }.bind(this));


	    $j("body").on("schedule-changed", this.render.bind(this));
    }
    this.init();

}

/**
 * This is one row in the directory containing a section to be scheduled
 */
function TableRow(section, el, directory){
    this.el = el;
    this.section = section;
    this.directory = directory;
    
    this.cell = new Cell($j("<td/>"), section, null, null, this.directory.matrix);

    this.render = function(){
	    this.el[0].innerHTML = "<td>" + this.section.title + "</td>";
	    this.el.append(this.cell.el);
    };

    this.hide = function(){
	    this.el.css("display", "none");
    };

    this.unHide = function(){
	    this.el.css("display", "table-row");
    };
}

