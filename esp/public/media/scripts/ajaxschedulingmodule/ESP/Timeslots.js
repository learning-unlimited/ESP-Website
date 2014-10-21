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
}
