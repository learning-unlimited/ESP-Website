describe("Timeslots", function(){
    var t;
    var one_hour_section;
    var two_hour_section;

    beforeEach(function(){
	t = new Timeslots(time_fixture())
	one_hour_section =  {
            length: 0.83
	}
	two_hour_section =  {
            length: 1.83
	}
    })

    it("returns timeslots by id", function(){
	o = time_fixture_with_order()
	expect(t.get_by_id(1)).toEqual(o[1])
	expect(t.get_by_id(2)).toEqual(o[2])
    })

    it("returns timeslots by order", function(){
	o = time_fixture_with_order()
	expect(t.get_by_order(0)).toEqual(o[1])
	expect(t.get_by_order(1)).toEqual(o[2])	
    })

    describe("get_timeslots_to_schedule_section", function(){
	var section

	beforeEach

	describe("a one hour class", function(){
            it("returns the timeslot passed", function(){
		expect(t.get_timeslots_to_schedule_section(one_hour_section, 1)).toEqual([1])
            })
	})

	describe("a two hour class", function(){
            it("returns the timeslot passed and the next one", function(){
		expect(t.get_timeslots_to_schedule_section(two_hour_section, 1)).toEqual([1,2])
            })
        })
	describe("when scheduling over the day break", function(){
	    it("returns null", function(){
		var times = {
		    1: {
			id: 1,
			start: [2010, 4, 17, 10, 0, 0],
			end: [2010, 4, 17, 10, 50, 0]
		    },
		    2: {
			id: 2,
			start: [2010, 4, 18, 10, 0, 0],
			end: [2010, 4, 18, 10, 50, 0]
		    }
		}
		t = new Timeslots(times)
		expect(t.get_timeslots_to_schedule_section(two_hour_section, 1)).toEqual(null)
	    })
	})
     })

    describe("get_timeslot_length", function(){
       it("returns 1 for a .83 hour timeslot", function(){
	   var times = {
	       1: {
		   id: 1,
		   start: [2010, 4, 17, 10, 0, 0],
		   end: [2010, 4, 17, 10, 50, 0]
	       }
	   }
	   t = new Timeslots(times)
           expect(t.get_time_between(1, 1)).toEqual(1)
       })

       it("returns 1 for a 1 hour timeslot", function(){
	   var times = {
	       1: {
		   id: 1,
		   start: [2010, 4, 17, 10, 0, 0],
		   end: [2010, 4, 17, 11, 0, 0]
	       }
	   }
	   t = new Timeslots(times)
           expect(t.get_time_between(1, 1)).toEqual(1)
       })

       it("returns 2 for a 1.83 hour timeslot", function(){
	   var times = {
	       1: {
		   id: 1,
		   start: [2010, 4, 17, 10, 0, 0],
		   end: [2010, 4, 17, 10, 50, 0]
	       },
	       2: {
		   id: 2,
		   start: [2010, 4, 17, 11, 0, 0],
		   end: [2010, 4, 17, 11, 50, 0]
	       }
	   }
	   t = new Timeslots(times)
           expect(t.get_time_between(1, 2)).toEqual(2)
       })
    })
})
