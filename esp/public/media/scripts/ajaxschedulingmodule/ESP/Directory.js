function Directory(sections, el, schedule_assignments) {
    this.sections = sections;
    this.el = el;
    this.schedule_assignments = schedule_assignments;

    this.render = function(){
	var oldChildren = this.el.children();
	$j.each(oldChildren, function(c){
	    oldChildren[c].hidden = true;
	});

	setTimeout(function(){
	    $j.each(oldChildren, function(c){
		oldChildren[c].remove();
	    });
	}.bind(this), 0);
	var table = $j("<table/>");
	$j.each(this.filtered_sections(), function(id, section){
	    var row = new TableRow(section, $j("<tr/>"));
	    row.render();
	    row.el.appendTo(table);
	})
	table.appendTo(this.el);
    };

    this.init = function(){
	$j("body").on("schedule-changed", this.render.bind(this));
    }
    this.init();

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

function TableRow(section, el){
    this.el = el;
    this.section = section;
    this.cell = new Cell($j("<td/>"), section);

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

