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
	    $j.each(this.filtered_sections(), function(id, section){
	        var row = new TableRow(section, $j("<tr/>"), this);
	        row.render();
	        row.el.appendTo(table);
	    }.bind(this))
	        table.appendTo(this.el);
    };

    this.init = function(){
	    $j("body").on("schedule-changed", this.render.bind(this));
    }
    this.init();

    /**
     * Get the sections that are not yet scheduled
     */
    this.filtered_sections = function(){
	    var returned_sections = [];
	    for (i in this.sections){
	        var section = this.sections[i];
	        if (schedule_assignments[section.id] && schedule_assignments[section.id].room_name == null){
		        returned_sections.push(section);
	        }
	    }
	    return returned_sections;
    };
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

