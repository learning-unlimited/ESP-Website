describe("Timeslots", function(){
    it("returns timeslots by id", function(){
	t = new Timeslots(time_fixture())
	o = time_fixture_with_order()
	expect(t.get_by_id(1)).toEqual(o[1])
	expect(t.get_by_id(2)).toEqual(o[2])
    })

    it("returns timeslots by order", function(){
	t = new Timeslots(time_fixture())
	o = time_fixture_with_order()
	expect(t.get_by_order(0)).toEqual(o[1])
	expect(t.get_by_order(1)).toEqual(o[2])	
    })
})
