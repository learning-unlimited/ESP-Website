function Directory(sections, el) {
    this.sections = sections
    this.el = el
    this.render = function(){
	table = $j("<table/>")
	$j.each(sections, function(id, section){
	    row = new TableRow(section, $j("<tr/>"))
	    row.render()
	    row.el.appendTo(table)
	})
	table.appendTo(this.el)
    }
}

function TableRow(section, el){
    this.el = el
    this.section = section
    this.cell = new Cell($j("<td/>"))
    //TODO:  I should be able to create a cell with a section
    this.cell.addSection(section)

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

