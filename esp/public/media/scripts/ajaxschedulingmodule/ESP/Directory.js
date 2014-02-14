function Directory(sections, el) {
    this.sections = sections
    this.el = el
    this.render = function(){
	table = $j("<table/>")
	$j.each(sections, function(id, section){
	    row = $j("<tr><td>" + section.title + "</td><td>"+section.emailcode+"</td></tr>")
	    row.appendTo(table)
	})
	table.appendTo(this.el)
    }
}

