helpers_add_timeslots_order = function(timeslot_object){
    var timeslot_array = []
    $j.each(timeslot_object, function(timeslot_id, timeslot){
	timeslot_array.push(timeslot)
    })

    var sorted_timeslot_array = timeslot_array.sort(function(a,b){
	for (i=0; i<a.start.length; i++){
	    var comp = a.start[i] - b.start[i]
	    if (comp != 0){
		return comp
	    }
	}
	return 0
    })

    for (i=0; i<sorted_timeslot_array.length; i++){
	var t = sorted_timeslot_array[i]
	timeslot_object[t.id].order = i
    }

    return timeslot_object
}
