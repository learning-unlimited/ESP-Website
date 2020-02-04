describe("Helpers", function(){
        describe("add_timeslots_order", function(){
            it("puts the timeslots in order", function() {
                var original_timeslots = time_fixture();
                var ordered_timeslots = helpers_add_timeslots_order(original_timeslots);
                expect(original_timeslots['3'].order).toEqual(0);
                expect(original_timeslots['5'].order).toEqual(1);
                expect(ordered_timeslots[0].id).toEqual(3);
                expect(ordered_timeslots[1].id).toEqual(5);
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

        describe("helpersIntersection", function() {
            it("returns the intersection of arrays", function() {
                var arrays1 = [[1, 2, 3, 4],
                [1, 3],
                [1]];
                var intersection1 = helpersIntersection(arrays1, true);
                expect(intersection1.length).toEqual(1);
                expect(intersection1[0]).toEqual(1);

                var arrays2 = [[1, 5, 7, 9],
                [2 , 3]];
                var intersection2 = helpersIntersection(arrays2, true);
                expect(intersection2.length).toEqual(0);
                });
            });
});
