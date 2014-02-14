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

    this.render = function(){
	this.el[0].innerHTML = "<td>" + this.section.title + "</td><td>"+this.section.emailcode+"</td>"
	this.el.draggable()
    }
}

