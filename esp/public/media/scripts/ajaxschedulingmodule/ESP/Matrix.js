function Matrix(timeslots, rooms, schedule_assignments, sections, el) {
    //TODO:  just pass the whole damn data object in
    this.el = el

    this.rooms = rooms
    this.schedule_assignments = schedule_assignments
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
		cells[room_name][i] = new Cell($j("<td/>"))
		i = i + 1
	    })
	})

	$j.each(schedule_assignments, function(class_id, assignment_data){
	    $j.each(assignment_data.timeslots, function(j, timeslot_id){
		class_emailcode = sections[class_id].emailcode
		timeslot_order = timeslots[timeslot_id].order
		//TODO:  augment timslots datastructure with order information
		cells[assignment_data.room_name][timeslot_order].addSection(sections[class_id])
	    })
	})
	return cells
    }()

    this.getCell = function(room_name, timeslot_id){
	return this.cells[room_name][this.timeslots[timeslot_id].order]
    }

    //TODO:  use scheduleClass in timeslots
    this.scheduleSection = function(section, room_name, schedule_timeslots){
	//validation
	for(timeslot_index in schedule_timeslots){
	    timeslot_id = schedule_timeslots[timeslot_index]
	    if (this.getCell(room_name, timeslot_id).section != null){
		return false
	    }
	}

	for(timeslot_index in schedule_timeslots){
	    timeslot_id = schedule_timeslots[timeslot_index]
	    this.getCell(room_name, timeslot_id).addSection(section)
	}
	return true
    }

    this.clearCell = function(cell){
	cell.removeSection()
    }

    this.render = function(){
	table = $j("<table/>")

	//Time headers
	header_row = $j("<tr/>").appendTo($j("<thead/>").appendTo(table))
	$j("<th/>").appendTo(header_row)
	$j.each(this.timeslots, function(id, timeslot){
	    $j("<th>" + timeslot.label + "</th>").appendTo(header_row)
	})

	//Room headers
	rows = {}	//table rows by room name
	$j.each(this.rooms, function(id, room){
	    row = $j("<tr><th>" + id + "</th></tr>")
	    rows[id] = row
	    row.appendTo(table)
	})

	//populate cells
	cells = this.cells	//TODO:  what are you actually supposed to do here?
	$j.each(this.rooms, function(id, room){
	    row = rows[id]
	    for(i = 0; i < Object.keys(timeslots).length; i++){
		//TODO:  use getCell here
		cells[id][i].el.appendTo(row)
	    }
	})
	table.appendTo(this.el)
    }
}

