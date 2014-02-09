function Directory(sections, el) {
    this.sections = sections
    this.el = el
    this.render = function(){
	table = $("<table/>")[0]
	$(sections).each(function(i, section){
	    row = $("<tr><td>" + section.title + "</td></tr>")[0]
	    table.appendChild(row)
	})
	this.el.appendChild(table)
    }
}

function Matrix() {
}

function Scheduler(data, directoryEl) {
    this.directory = new Directory(data.sections, directoryEl)
    this.matrix = new Matrix()
}
