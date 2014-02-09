function Directory(sections, el) {
    this.sections = sections
    this.el = el
    this.render = function(){
	table = $j("<table/>")[0]
	$j.each(sections, function(id, section){
	    row = $j("<tr><td>" + section.title + "</td></tr>")[0]
	    table.appendChild(row)
	})
	this.el.appendChild(table)
    }
}

function Matrix(el) {
    this.el = el
    this.render = function(){
    }
}

function Scheduler(data, directoryEl, matrixEl) {
    this.directory = new Directory(data.sections, directoryEl)
    this.matrix = new Matrix(matrixEl)
    this.render = function(){
	this.directory.render()
	this.matrix.render()
    }
}
