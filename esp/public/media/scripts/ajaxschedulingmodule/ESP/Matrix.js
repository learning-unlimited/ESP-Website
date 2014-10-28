function Matrix(
    timeslots,
    rooms,
    schedule_assignments,
    sections,
    el,
    garbage_el,
    api_client
){ 
    this.el = el
    this.garbage_el = garbage_el
    this.el.id = "matrix-table"

    this.rooms = rooms
    this.schedule_assignments = schedule_assignments
    this.sections = sections
    this.timeslots = new Timeslots(timeslots)

    this.api_client = api_client

    // garbage stuff
    this.garbageDropHandler = function(ev, ui){
	this.unscheduleSection(ui.draggable.data("section"))
    }.bind(this)

    // set up drophandler
    this.dropHandler = function(el, ui){
	var cell = $j(el.currentTarget).data("cell")
	var section = ui.draggable.data("section")
	this.scheduleSection(section, cell.room_name, cell.timeslot_id)
    }.bind(this)

    this.init = function(){
	this.el.on("drop", "td", this.dropHandler)
	this.garbage_el.droppable({
	    drop: this.garbageDropHandler
	}) 
    }

    this.init()

    // set up cells
    this.cells = function(){
	var cells = {}
	$j.each(rooms, function(room_name, room){
	    cells[room_name] = []
	    i = 0
	    $j.each(timeslots, function(timeslot_id_string, timeslot){
		var timeslot_id = parseInt(timeslot_id_string)
		cells[room_name][i] = new Cell($j("<td/>"), null, room_name, timeslot_id)
		i = i + 1
	    })
	})

	$j.each(schedule_assignments, function(class_id, assignment_data){
	    $j.each(assignment_data.timeslots, function(j, timeslot_id){
		var class_emailcode = sections[class_id].emailcode
		var timeslot_order = timeslots[timeslot_id].order
		cells[assignment_data.room_name][timeslot_order].addSection(sections[class_id])
	    })
	})
	return cells
    }()

    this.getCell = function(room_name, timeslot_id){
	return this.cells[room_name][this.timeslots.get_by_id(timeslot_id).order]
    }

    this.validateAssignment = function(section, room_name, schedule_timeslots){
	for(timeslot_index in schedule_timeslots){
	    var timeslot_id = schedule_timeslots[timeslot_index]
	    if (this.getCell(room_name, timeslot_id).section != null){
		return false
	    }
	}
	return true
    }

    // scheduling sections
    this.scheduleSection = function(section, room_name, first_timeslot_id){
	schedule_timeslots = this.timeslots.get_timeslots_to_schedule_section(section, first_timeslot_id)
	if (!this.validateAssignment(section, room_name, schedule_timeslots)){
	    return
	}

	this.api_client.schedule_section(
	    section.id, 
	    //TODO: schedule_timeslots instead of first_timeslot_id
	    schedule_timeslots,
	    room_name, 
	    function() {
		this.scheduleSectionLocal(section, room_name, schedule_timeslots)
	    }.bind(this),
	    function(msg) {
		console.log(msg)
	    } 
	)
    }

    this.scheduleSectionLocal = function(section, room_name, schedule_timeslots){
	for(timeslot_index in schedule_timeslots){
	    var timeslot_id = schedule_timeslots[timeslot_index]
	    this.getCell(room_name, timeslot_id).addSection(section)
	}

	//Unschedule from old place
	var old_assignment = this.schedule_assignments[section.id]
	for (timeslot_index in old_assignment.timeslots) {
	    var timeslot_id = old_assignment.timeslots[timeslot_index]
	    var cell = this.getCell(old_assignment.room_name, timeslot_id)
	    cell.removeSection()
	}

	this.schedule_assignments[section.id] = {
	    room_name: room_name,
	    timeslots: schedule_timeslots,
	    id: section.id
	}

	$j("body").trigger("schedule-changed")
    }

    this.unscheduleSection = function(section){
	this.api_client.unschedule_section(
	    section.id, 
	    function(){ 
		this.unscheduleSectionLocal(section) 
	    }.bind(this),
	    function(msg){
		console.log(msg)
	    }
	)
    }

    this.unscheduleSectionLocal = function(section) {
	var assignment = this.schedule_assignments[section.id]
	var cell = this.getCell(assignment.room_name, assignment.timeslots[0])
	this.clearCell(cell)

	this.schedule_assignments[section.id] = { room_name: null, timeslots: [], id: section.id}

	$j("body").trigger("schedule-changed")
    }

    this.clearCell = function(cell){
	cell.removeSection()
    }

    // render
    this.render = function(){
	var table = $j("<table/>")

	//Time headers
	var header_row = $j("<tr/>").appendTo($j("<thead/>").appendTo(table))
	$j("<th/>").appendTo(header_row)
	$j.each(timeslots, function(id, timeslot){
	    $j("<th>" + timeslot.label + "</th>").appendTo(header_row)
	})

	//Room headers
	var rows = {}	//table rows by room name
	$j.each(this.rooms, function(id, room){
	    var row = $j("<tr><th>" + id + "</th></tr>")
	    rows[id] = row
	    row.appendTo(table)
	})

	//populate cells
	var cells = this.cells
	$j.each(this.rooms, function(id, room){
	    row = rows[id]
	    for(i = 0; i < Object.keys(timeslots).length; i++){
		cells[id][i].el.appendTo(row)
	    }
	})
	table.appendTo(this.el)
    }
}

