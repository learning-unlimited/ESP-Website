describe("Helpers", function(){
    describe("add_timeslots_order", function(){
	    it("puts the timeslots in order", function() {
	        var original_timeslots = time_fixture_out_of_order();
	        var ordered_timeslots = helpers_add_timeslots_order(original_timeslots);
	        expect(ordered_timeslots['2'].order).toEqual(0);
	        expect(ordered_timeslots['1'].order).toEqual(1);
	    });
    });
    
    describe("helpers_hex_string_to_color", function() {
        it("returns the corect color", function() {
            var hex_string = "#55ff33";
            var color = helpers_hex_string_to_color(hex_string);
            expect(color[0]).toEqual(85);
            expect(color[1]).toEqual(255);
            expect(color[2]).toEqual(51);
        });
    });
});
