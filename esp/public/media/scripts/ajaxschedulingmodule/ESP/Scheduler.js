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

function Matrix(timeslots, rooms, schedule_assignments, el) {
    this.el = el
    this.timeslots = timeslots
    this.rooms = rooms
    this.schedule_assigments = schedule_assignments
    
    this.cells = function(){
	cells = {}
	ts = timeslots
	$j.each(rooms, function(room_name, room){
	    cells[room_name] = []
	    i = 0
	    $j.each(ts, function(timeslot_id, timeslot){
		cells[room_name][i] = $j("<td/>")[0]
		i = i + 1
	    })
	})
	return cells
    }()

    this.render = function(){
	table = $j("<table/>")[0]

	//Time headers
	header_row = table.createTHead().insertRow(0)
	header_row.appendChild($j("<th/>")[0])
	$j.each(this.timeslots, function(id, timeslot){
	    cell = $j("<th>" + timeslot.label + "</th>")[0]
	    header_row.appendChild(cell)
	})

	//Room headers
	rows = {}	//table rows by room name
	$j.each(this.rooms, function(id, room){
	    row = $j("<tr><th>" + id + "</th></tr>")[0]
	    rows[id] = row
	    table.appendChild(row)
	})

	//populate cells
	cells = this.cells	//TODO:  what are you actually supposed to do here?
	$j.each(this.rooms, function(id, room){
	    row = rows[id]
	    for(i = 0; i < Object.keys(timeslots).length; i++){
		row.appendChild(cells[id][i])
	    }
	})
	this.el.appendChild(table)	
    }
}

function Scheduler(data, directoryEl, matrixEl) {
    this.directory = new Directory(data.sections, directoryEl)
    this.matrix = new Matrix(data.timeslots, data.rooms, data.schedule_assignments, matrixEl)
    this.render = function(){
	this.directory.render()
	this.matrix.render()
    }
}
