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

function Matrix(timeslots, rooms, el) {
    this.el = el
    this.timeslots = timeslots
    this.rooms = rooms
    this.render = function(){
	table = $j("<table/>")[0]
	header_row = table.createTHead().insertRow(0)
	header_row.appendChild($j("<th/>")[0])
	$j.each(timeslots, function(id, timeslot){
	    cell = $j("<th>" + timeslot.label + "</th>")[0]
	    header_row.appendChild(cell)
	})
	$j.each(rooms, function(id, room){
	    row = $j("<tr><th>" + id + "</th></tr>")[0]
	    table.appendChild(row)
	})
	this.el.appendChild(table)	
    }
}

function Scheduler(data, directoryEl, matrixEl) {
    this.directory = new Directory(data.sections, directoryEl)
    this.matrix = new Matrix(data.timeslots, data.rooms, matrixEl)
    this.render = function(){
	this.directory.render()
	this.matrix.render()
    }
}
