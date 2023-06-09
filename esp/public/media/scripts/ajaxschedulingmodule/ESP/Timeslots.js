/**
 * Stores timeslot data and provides convenience methods
 *
 * @param timeslots_data: The raw timeslot data
 */
function Timeslots(timeslots_data, lunch_timeslots){
    /**
     * Add the "order" property to each timeslot which is equal to its rank when
     * sorted by start time.
     */
    this.helpers_add_timeslots_order = function(timeslot_object){
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

        return sorted_timeslot_array;
    };
    this.timeslots_sorted = this.helpers_add_timeslots_order(timeslots_data);
    this.timeslots = timeslots_data;
    this.lunch_timeslots = {};

    if(lunch_timeslots) {
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
    }

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
        return this.timeslots_sorted[order];
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
        while (this.get_hours_spanned(first_timeslot_id, last_timeslot_id) < section.length){
            var last_timeslot = this.get_by_id(last_timeslot_id);
            next_timeslot = this.get_by_order(last_timeslot.order + 1);

            if (next_timeslot === undefined || !this.are_timeslots_contiguous([last_timeslot, next_timeslot])){
                return null;
            }
            last_timeslot_id = next_timeslot.id;
            times.push(next_timeslot.id);
        }
        return times;
    };

    /**
     * Get the number of hours spanned by the two timeslots with ids id_1 and id_2
     */
    this.get_hours_spanned = function(id_1, id_2) {
        var start = new Date(...this.timeslots[id_1].start);
        var end = new Date(...this.timeslots[id_2].end);

        return Math.round((((end - start)/3600000) + Number.EPSILON) * 100) / 100;
    };

    /**
     * Get the number of minutes between the two timeslots with ids id_1 and id_2
     */
    this.get_minutes_between = function(id_1, id_2) {
        var end = new Date(...this.timeslots[id_1].end);
        var start = new Date(...this.timeslots[id_2].start);

        return (start - end)/60000;
    };

    // the minimum time difference between timeslots
    // defined by the "timeblock_contiguous_tolerance" program tag
    this.minimumDifference = parseInt(contiguous_tolerance);    

    /**
     * Returns a guess of whether the specified timeslots are contiguous in time
     */
    this.are_timeslots_contiguous = function(timeslots) {
        // we use the minimum time difference between timeslots as an
        //   expected "passing period" duration; then, we just check
        //   whether the given timeslots are within that period
        // we also fail if any timeslot isn't in the right order or same day
        // if we encounter anything unexpected, we return true to avoid
        //   incorrectly adding a constraint on scheduling
        if (this.minimumDifference === false){
            return true;
        }
        for(var i = 0; i < timeslots.length - 1; i++){
            if (timeslots[i].order + 1 != timeslots[i + 1].order ||
                !this.on_same_day(timeslots[i], timeslots[i + 1])){
                return false;
            }
            var difference = this.get_minutes_between(timeslots[i].id, timeslots[i + 1].id);
            if (difference > this.minimumDifference){
                return false;
            }
        }
        return true;
    };
};