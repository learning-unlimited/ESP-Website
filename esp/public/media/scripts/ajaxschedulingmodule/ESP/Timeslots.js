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

            if (!this.are_timeslots_contiguous([last_timeslot, next_timeslot])){
                console.log("timeslot " + last_timeslot.id + " and timeslot " +
                        next_timeslot.id +" are not contiguous");
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
        var start = this.timeslots[id_1].start;
        var end = this.timeslots[id_2].end;

        var hours = end[3] - start[3];
        var minutes = end[4] - start[4];

        if (minutes > 0){
            hours = hours + 1;
        }
        return hours;
    };

    /**
     * Get the number of minutes between the two timeslots with ids id_1 and id_2
     */
    this.get_minutes_between = function(id_1, id_2) {
        var end = this.timeslots[id_1].end;
        var start = this.timeslots[id_2].start;

        var hours = start[3] - end[3];
        var minutes = start[4] - end[4];
        return hours * 60 + minutes;
    };

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

    // compute the minimum time difference between timeslots
    //  (this is used in this.are_timeslots_contiguous)
    var minimumDifference = false;
    for(var i = 0; i < this.timeslots_sorted.length - 1; i++) {
        var currentTimeslot = this.timeslots_sorted[i];
        var nextTimeslot = this.timeslots_sorted[i + 1];
        if (!this.on_same_day(currentTimeslot, nextTimeslot)){
            continue;
        }
        var difference = this.get_minutes_between(currentTimeslot.id, nextTimeslot.id);
        if (minimumDifference === false || difference < minimumDifference){
            minimumDifference = difference;
        }
    }
    this.minimumDifference = minimumDifference;
};
