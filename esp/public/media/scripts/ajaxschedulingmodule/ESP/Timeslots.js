function Timeslots(timeslots_data){
    // TODO: move helper to add timeslot order here
    this.timeslots = helpers_add_timeslots_order(timeslots_data)

    this.get_by_id = function(id){
	return this.timeslots[id]
    }

    this.get_by_order = function(order){
	for (id in this.timeslots){
	    if (this.timeslots[id].order == order){
		return this.timeslots[id]
	    }
	}	
    }

    this.get_timeslots_to_schedule_section = function(section, first_timeslot_id){
	var times = [first_timeslot_id]
	var last_timeslot_id = first_timeslot_id
	while (this.get_time_between(first_timeslot_id, last_timeslot_id) < section.length){
	    var last_timeslot = this.get_by_id(last_timeslot_id)
	    last_timeslot_id = this.get_by_order(last_timeslot.order + 1).id
	    times.push(last_timeslot_id)
	}
	return times
    }

    this.get_time_between = function(id_1, id_2) {
	var start = this.timeslots[id_1].start
	var end = this.timeslots[id_2].end

	var hours = end[3] - start[3]
	var minutes = end[4] - start[4]

	if (minutes > 0){
	    hours = hours + 1
	}
	return hours
    }
}
