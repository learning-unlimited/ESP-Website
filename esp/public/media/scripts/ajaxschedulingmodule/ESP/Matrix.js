function Matrix(timeslots, rooms, schedule_assignments, sections, el) {
    //TODO:  just pass the whole damn data object in
    this.el = el

    this.rooms = rooms
    this.schedule_assigments = schedule_assignments
    this.sections = sections
    
    this.add_timeslots_order = function(timeslot_object){
	//TODO test and actually implement this
	//TODO should this be a helper elsewhere
	i = 0
	$j.each(timeslot_object, function(timeslot_id, timeslot){
	    timeslot.order = i
	    i = i+1
	})
	return timeslot_object
    }

    this.timeslots = this.add_timeslots_order(timeslots)

    this.cells = function(){
	cells = {}
	$j.each(rooms, function(room_name, room){
	    cells[room_name] = []
	    i = 0
	    $j.each(timeslots, function(timeslot_id, timeslot){
		cells[room_name][i] = $j("<td class='available-cell matrix-cell'/>")[0]
		i = i + 1
	    })
	})

	$j.each(schedule_assignments, function(class_id, assignment_data){
	    $j.each(assignment_data.timeslots, function(j, timeslot_id){
		class_emailcode = sections[class_id].emailcode
		timeslot_order = timeslots[timeslot_id].order
		//TODO:  augment timslots datastructure with order information
		cells[assignment_data.room_name][timeslot_order] = $j("<td class='occupied-cell matrix-cell'>"+class_emailcode+"</td>")[0]
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

