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

    describe("get_timeslot_length", function(){
        it("returns 1 for a .83 hour timeslot", function(){
            expect(t.get_hours_spanned(3, 3)).toEqual(1);
        });

        it("returns 1 for a 1 hour timeslot", function(){
            times[3].length = 1;
            t = new Timeslots(times);
            expect(t.get_hours_spanned(3, 3)).toEqual(1);
        });

        it("returns 2 for a 1.83 hour timeslot", function(){
            expect(t.get_hours_spanned(3, 5)).toEqual(2);
        });
    });
});
