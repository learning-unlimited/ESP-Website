const { section_1, section_2, time_fixture } = require("./TestFixtures");

describe("Timeslots", function(){
    var t, times;
    var one_hour_section;
    var two_hour_section;

    beforeEach(function() {
        times = time_fixture();
        t = new Timeslots(times);
        one_hour_section = section_1();
        two_hour_section = section_2();
    });

    it("returns timeslots by id", function(){
        expect(t.get_by_id(3)).toEqual(times[3]);
        expect(t.get_by_id(5)).toEqual(times[5]);
    });

    it("returns timeslots by order", function(){
        expect(t.get_by_order(0)).toEqual(times[3]);
        expect(t.get_by_order(1)).toEqual(times[5]);
    });

    describe("helpers_add_timeslots_order", function(){
        it("puts the timeslots in order", function() {
            var original_timeslots = time_fixture();
            var ordered_timeslots = t.helpers_add_timeslots_order(original_timeslots);
            expect(original_timeslots[3].order).toEqual(0);
            expect(original_timeslots[5].order).toEqual(1);
            expect(ordered_timeslots[0].id).toEqual(3);
            expect(ordered_timeslots[1].id).toEqual(5);
        });
    });

    describe("get_timeslots_to_schedule_section", function(){
        describe("a one hour class", function(){
            it("returns the timeslot passed", function(){
                expect(t.get_timeslots_to_schedule_section(one_hour_section, 3)).toEqual([3]);
            });
        });

        describe("a two hour class", function(){
            it("returns the timeslot passed and the next one", function(){
                expect(t.get_timeslots_to_schedule_section(two_hour_section, 3)).toEqual([3,5]);
            });
        });

        describe("when scheduling over the day break", function(){
            it("returns null", function(){
                expect(t.get_timeslots_to_schedule_section(two_hour_section, 5)).toEqual(null);
            });
        });
    });

    describe("are_timeslots_contiguous", function(){
        it("accepts timeslots within contiguous_tolerance minutes of each other", function(){
            expect(t.are_timeslots_contiguous([times[3], times[5]])).toBe(true);
        });

        it("rejects timeslots further apart than contiguous_tolerance minutes", function(){
            times[5].start = [2010, 4, 17, 11, 30, 0];
            t = new Timeslots(times);
            expect(t.are_timeslots_contiguous([times[3], times[5]])).toBe(false);
        });

        it("rejects timeslots on different days", function(){
            expect(t.are_timeslots_contiguous([times[5], times[7]])).toBe(false);
        });
    });

    describe("get_hours_spanned", function(){
        it("returns .83 for a 50 minute timeslot", function(){
            expect(t.get_hours_spanned(3, 3)).toEqual(.83);
        });

        it("returns 1 for a 1 hour timeslot", function(){
            times[3].end = [2010, 4, 17, 11, 5, 0];
            t = new Timeslots(times);
            expect(t.get_hours_spanned(3, 3)).toEqual(1);
        });

        it("returns 1.83 for two 50 minute timeslots", function(){
            expect(t.get_hours_spanned(3, 5)).toEqual(1.83);
        });
    });
});
