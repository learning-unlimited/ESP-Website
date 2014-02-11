function Directory(sections, el) {
    this.sections = sections
    this.el = el
    this.render = function(){
	table = $j("<table/>")[0]
	$j.each(sections, function(id, section){
	    row = $j("<tr><td>" + section.title + "</td><td>"+section.emailcode+"</td></tr>")[0]
	    table.appendChild(row)
	})
	this.el.appendChild(table)
    }
}

