describe("Matrix", function(){
    beforeEach(function(){
	m = new Matrix(
	    time_fixture(),
	    room_fixture(),
	    schedule_assignments_fixture(),
	    sections_fixture(),
	    $j("<div/>"), $j("<div/>"),
	    new FakeApiClient())
    })

    it("should have an element and a garbage element", function(){
	expect(m.el[0]).toBeHtmlNode()
	expect(m.garbage_el[0]).toBeHtmlNode()
    })

    it("should have times, rooms, and schedule assignments", function(){
	expect(m.timeslots).toBeObject()
	expect(m.rooms).toBeObject()
	expect(m.schedule_assignments).toBeObject()
	expect(m.sections).toBeObject()
    })

    describe("getCell", function(){
	it("returns the html cell for the requested room and time", function(){
	    expect(m.getCell("room-1", 1).section).toEqual(section_1())
	    expect(m.getCell("room-1", 1).room_name).toEqual("room-1")
	    expect(m.getCell("room-1", 1).timeslot_id).toEqual(1)

	    expect(m.getCell("room-1", 2).section).toEqual(section_1())
	    expect(m.getCell("room-1", 2).room_name).toEqual("room-1")
	    expect(m.getCell("room-1", 2).timeslot_id).toEqual(2)

	    expect(m.getCell("room-2", 1).innerHTML).toEqual(null)
	    expect(m.getCell("room-2", 1).room_name).toEqual("room-2")
	    expect(m.getCell("room-1", 1).timeslot_id).toEqual(1)

	    expect(m.getCell("room-2", 2).innerHTML).toEqual(null)
	    expect(m.getCell("room-2", 2).room_name).toEqual("room-2")
	    expect(m.getCell("room-1", 2).timeslot_id).toEqual(2)
	})
    })
   
    describe("scheduleSection", function(){
	it("inserts the class into the matrix", function(){
	    cell1 = m.getCell("room-2", 1)
	    cell2 = m.getCell("room-2", 2)
	    spyOn(cell1, 'addSection')
	    spyOn(cell2, 'addSection')
	    expect(m.scheduleSection(section_2(), "room-2", [1,2])).toBeTrue()
	    expect(cell1.addSection).toHaveBeenCalledWith(section_2())
	    expect(cell2.addSection).toHaveBeenCalledWith(section_2())
	    expect(m.schedule_assignments[section_2().id]).toEqual({room_name: "room-2", timeslots: [1, 2], id: section_2().id})
	})

	it("unschedules the class from the old location", function(){

	    cell1 = m.getCell("room-1", 1)
	    cell2 = m.getCell("room-1", 2)
	    spyOn(cell1, 'removeSection')
	    spyOn(cell2, 'removeSection')
	    expect(m.scheduleSection(section_1(), "room-2", [1,2])).toBeTrue()
	    expect(cell1.removeSection).toHaveBeenCalled()
	    expect(cell2.removeSection).toHaveBeenCalled()
	    expect(m.schedule_assignments[section_1().id]).toEqual({room_name: "room-2", timeslots: [1, 2], id: section_1().id})
	})

	it("fires a schedule-changed event", function(){
	    event_fired = false
	    $j("body").on("schedule-changed", function(){
		event_fired = true
	    })
	    m.scheduleSection(section_2(), "room-2", [1,2])
	    expect(event_fired).toBeTrue()
	})

	describe("validation", function(){
	    describe("when a class is already scheduled in a room", function(){
		beforeEach(function(){
		    m.scheduleSection(section_1(), "room-2", [2])
		})
		
		it("returns false", function(){
		    expect(m.scheduleSection(section_2(), "room-2", [1,2])).toBeFalse()
		})
		it("doesn't allow you to schedule the class", function(){
		    m.scheduleSection(section_2(), "room-2", [1,2])
		    expect(m.getCell("room-2", 1).section).not.toEqual(section_2())
		    expect(m.getCell("room-2", 2).section).not.toEqual(section_2())
		})
	    })

	    describe("when the api call fails", function(){
		beforeEach(function(){
		    m.api_client = new FakeFailingApiClient()
		})
		it("returns false", function(){
		    expect(m.scheduleSection(section_2(), "room-2", [1,2])).toBeFalse()
		})
		it("doesn't allow you to schedule the class", function(){
		    m.scheduleSection(section_2(), "room-2", [1,2])
		    expect(m.getCell("room-2", 1).section).not.toEqual(section_2())
		    expect(m.getCell("room-2", 2).section).not.toEqual(section_2())
		})

	    })
	})

	afterEach(function() {
	    m.clearCell(m.getCell("room-2", 1))
	    m.clearCell(m.getCell("room-2", 2))
	})
    })

    describe("unscheduleSection", function(){
	it("removes the class from the matrix", function(){
	    expect(m.getCell("room-1", 1).section).toEqual(section_1())
	    m.unscheduleSection(section_1())
	    expect(m.getCell("room-1", 1).section).not.toEqual(section_1())
	})

	it("fires a schedule-changed event", function(){
	    event_fired = false
	    $j("body").on("schedule-changed", function(){
		event_fired = true
	    })
	    m.unscheduleSection(section_1())
	    expect(event_fired).toBeTrue()
	})

	it("modifies the schedule_assignments data structure", function(){
	    expect(m.schedule_assignments[section_1().id]).toEqual({room_name: "room-1", timeslots: [1,2], id: section_1().id})
	    m.unscheduleSection(section_1())
	    expect(m.schedule_assignments[section_1().id]).toEqual({room_name: null, timeslots: [], id: section_1().id})
	})

	describe("when the API client returns an error", function(){
	    beforeEach(function(){
		m.api_client = new FakeFailingApiClient()
	    })
	    it("doesn't unschedule the class", function(){
		m.unscheduleSection(section_1())
		expect(m.schedule_assignments[section_1().id]).toEqual({room_name: "room-1", timeslots: [1,2], id: section_1().id})
		expect(m.getCell("room-1", 1).section).toEqual(section_1())
	    })
	})
    })

    describe("clearCell", function(){
	it("removes a section from that cell", function(){
	    cell = m.getCell("room-1", 1)
	    spyOn(cell, "removeSection")
	    expect(cell.section).not.toBeNull()
	    m.clearCell(m.getCell("room-1", 1))
	    expect(cell.removeSection).toHaveBeenCalled()
	})
    })

    describe("render", function(){
	beforeEach(function(){
	    m.render()
	})

	it("should have a row for each room", function(){
 	    expect(m.el.children().length).toEqual(1)
	    table = m.el.children()[0]
	    expect(table.rows.length).toEqual(3)
	    //TODO:  ordering should probably be deterministic, but I'm not sure how
	    expect(table.rows[1].cells[0].innerHTML).toMatch("room-1")
	    expect(table.rows[2].cells[0].innerHTML).toMatch("room-2")
	})

	it("should have a column each timeslot", function(){
	    table = m.el.children()[0]
	    
	    header = table.tHead
	    expect(header).toBeHtmlNode()
	    headers = header.rows[0].cells
	    expect(headers.length).toEqual(3)
	    //the corner block should be empty
	    expect(headers[1].innerHTML).toMatch("first timeslot")
	    expect(headers[2].innerHTML).toMatch("second timeslot")
	})

	it("should have a cell for every timeslot/room combination", function(){
	    table = m.el.children()[0]
	    expect(table.rows[1].cells[1]).toBeDefined()
	    expect(table.rows[1].cells[2]).toBeDefined()
	    expect(table.rows[2].cells[1]).toBeDefined()
	    expect(table.rows[2].cells[2]).toBeDefined()
	})

	it("should show already scheduled sections", function(){
	    table = m.el.children()[0]
	    expect(table.innerHTML).toMatch('S3188s1')
	})
    })
})
