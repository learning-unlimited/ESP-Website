/**
 * Stores timeslot data and provides convenience methods
 * 
 * @param timeslots_data: The raw timeslot data
 */
function Timeslots(timeslots_data, lunch_timeslots){
    // TODO: move helper to add timeslot order here
    this.timeslots_sorted = helpers_add_timeslots_order(timeslots_data);
    this.timeslots = timeslots_data; 
    this.lunch_timeslots = {};
    $j.each(lunch_timeslots, function(index, lunch_id) {
        var lunch_slot = this.timeslots[lunch_id];
        var lunch_slot_day = lunch_slot.end[2];
        if(this.lunch_timeslots[lunch_slot_day]) {
            this.lunch_timeslots[lunch_slot_day].push(lunch_slot);
        } else {
            this.lunch_timeslots[lunch_slot_day] = [lunch_slot];
        }
    }.bind(this)); 
    console.log(this.lunch_timeslots);

    /**
     * Get a timeslot by its id
     *
     * @param id: the id of the timeslot to get
     */
    this.get_by_id = function(id){
        return this.timeslots[id];
    };

    /**
     * Get a timeslot by its rank in the day based on start time
     * 
     * @param order: get the order-th timeslot
     */
    this.get_by_order = function(order){
        for (id in this.timeslots){
            if (this.timeslots[id].order == order){
                return this.timeslots[id];
            }
        }	
    };

    /**
     * Determine whether two timeslots occur on the same day.
     *
     * @param timeslot_1: first timeslot
     * @param timeslot_2: second timeslot
     */
    this.on_same_day = function(timeslot_1, timeslot_2){
        return timeslot_1.end[2] == timeslot_2.start[2];
    };

    /**
     * Get the timeslots to schedule a section during given the first timeslot we wish
     * to schedule it for.
     *
     * @param section: The section to get timeslots for
     * @param first_timeslot_id: The first timeslot to schedule the section in
     */
    this.get_timeslots_to_schedule_section = function(section, first_timeslot_id){
        var times = [first_timeslot_id];
        var last_timeslot_id = first_timeslot_id;
        while (this.get_time_between(first_timeslot_id, last_timeslot_id) < section.length){
            var last_timeslot = this.get_by_id(last_timeslot_id);
            next_timeslot = this.get_by_order(last_timeslot.order + 1);

            if (!this.on_same_day(last_timeslot, next_timeslot)){
                console.log("timeslot " + last_timeslot.id + " and timeslot " + 
                        next_timeslot.id +" are on different days");
                return null;
            }
            last_timeslot_id = next_timeslot.id;
            times.push(next_timeslot.id);
        }
        return times;
    };

    /**
     * Get the number of hours in between two timeslots with ids id_1 and id_2
     */
    this.get_time_between = function(id_1, id_2) {
        var start = this.timeslots[id_1].start;
        var end = this.timeslots[id_2].end;

        var hours = end[3] - start[3];
        var minutes = end[4] - start[4];

        if (minutes > 0){
            hours = hours + 1;
        }
        return hours;
    };
};
