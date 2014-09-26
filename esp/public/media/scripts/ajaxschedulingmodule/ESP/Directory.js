function Directory(sections, el, schedule_assignments) {
    this.sections = sections
    this.el = el
    this.schedule_assignments = schedule_assignments

    this.render = function(){
	this.el.empty()
	table = $j("<table/>")
	$j.each(this.filtered_sections(), function(id, section){
	    row = new TableRow(section, $j("<tr/>"))
	    row.render()
	    row.el.appendTo(table)
	})
	table.appendTo(this.el)
    }

    this.init = function(){
	$j("body").on("schedule-changed", this.render.bind(this))
    }
    this.init()

    this.filtered_sections = function(){
	returned_sections = []
	for (i in this.sections){
	    section = this.sections[i]
	    if (schedule_assignments[section.id] && schedule_assignments[section.id].room_name == null){
		returned_sections.push(section)
	    }
	}
	return returned_sections
    }
}

function TableRow(section, el){
    this.el = el
    this.section = section
    this.cell = new Cell($j("<td/>"), section)

    this.render = function(){
	this.el[0].innerHTML = "<td>" + this.section.title + "</td>"
	this.el.append(this.cell.el)
    }

    this.hide = function(){
	this.el.css("display", "none")
    }

    this.unHide = function(){
	this.el.css("display", "table-row")
    }
}

