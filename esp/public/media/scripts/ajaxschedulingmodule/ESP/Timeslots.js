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

    this.on_same_day = function(timeslot_1, timeslot_2){
	return timeslot_1.end[2] == timeslot_2.start[2]
    }

    this.get_timeslots_to_schedule_section = function(section, first_timeslot_id){
	var times = [first_timeslot_id]
	var last_timeslot_id = first_timeslot_id
	while (this.get_time_between(first_timeslot_id, last_timeslot_id) < section.length){
	    var last_timeslot = this.get_by_id(last_timeslot_id)
	    next_timeslot = this.get_by_order(last_timeslot.order + 1)

	    if (!this.on_same_day(last_timeslot, next_timeslot)){
		console.log("timeslot "+last_timeslot.id+" and timeslot "+ next_timeslot.id +" are on different days")
	        return null
	    }
	    last_timeslot_id = next_timeslot.id
	    times.push(next_timeslot.id)
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
