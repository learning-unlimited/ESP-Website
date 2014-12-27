describe("Helpers", function(){
    describe("add_timeslots_order", function(){
	it("puts the timeslots in order", function() {
	    var original_timeslots = time_fixture_out_of_order();
	    var ordered_timeslots = helpers_add_timeslots_order(original_timeslots);
	    expect(ordered_timeslots['2'].order).toEqual(0);
	    expect(ordered_timeslots['1'].order).toEqual(1);
	});
    });
});
