/**
 * Add the "order" property to each timeslot which is equal to its rank when
 * sorted by start time.
 */
helpers_add_timeslots_order = function(timeslot_object){
    var timeslot_array = [];
    $j.each(timeslot_object, function(timeslot_id, timeslot){
	    timeslot_array.push(timeslot);
    });

    // Sort timeslots by start time
    var sorted_timeslot_array = timeslot_array.sort(function(a,b){
	    for (i=0; i<a.start.length; i++) {
	        var comp = a.start[i] - b.start[i];
	        if (comp != 0) {
		        return comp;
	        }
	    }
	    return 0;
    });

    // Update the order in the original timeslot_object
    for (i=0; i<sorted_timeslot_array.length; i++){
	    var t = sorted_timeslot_array[i];
	    timeslot_object[t.id].order = i;
    }

    return timeslot_object;
};

/**
 * Takes hex string of form #rrggbb and outputs an array with rgb values
 */
helpers_hex_string_to_color = function(hex_string) {
    var color = [parseInt(hex_string.slice(1, 3), 16),
                 parseInt(hex_string.slice(3, 5), 16),
                 parseInt(hex_string.slice(5, 7), 16)];
    return color;
}
