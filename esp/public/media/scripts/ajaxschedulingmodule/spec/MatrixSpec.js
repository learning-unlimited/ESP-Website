describe("Matrix", function(){
    beforeEach(function(){
	m = new Matrix(time_fixture(), room_fixture(), schedule_assignments_fixture(), sections_fixture(), $j("<div/>"))
    })

    it("should have an element", function(){
	//TODO:  maybe we should assert that this is a jquery object?
	expect(m.el[0]).toBeHtmlNode()
    })

    it("should be droppable", function(){
	expect(m.el.droppable("option", "disabled")).toBeFalse()
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
	    expect(m.getCell("room-1", 2).section).toEqual(section_1())
	    expect(m.getCell("room-2", 1).innerHTML).toEqual(null)
	    expect(m.getCell("room-2", 2).innerHTML).toEqual(null)
	})
    })
    
    describe("dropHandler", function(){
	describe("get_timeslot_by_index", function(){
	    it("returns the correct timeslot object", function(){
		expect(m.get_timeslot_by_index(1).label).toEqual("first timeslot");
		expect(m.get_timeslot_by_index(2).label).toEqual("second timeslot");
	     })
	})

	//need to know both where we're coming from and where we are
	//figure out what cell we're in
	//validations
	//schedule into that cell
	//unschedule from the old cell
	//TODO:  send a notification to the server
    })

    describe("scheduleSection", function(){
	it("inserts the class into the matrix", function(){
	    cell1 = m.getCell("room-2", 1)
	    cell2 = m.getCell("room-2", 2)
	    spyOn(cell1, 'addSection')
	    spyOn(cell2, 'addSection')
	    expect(m.scheduleSection(section_2(), "room-2", [1,2])).toBeTrue()
	    expect(cell1.addSection).toHaveBeenCalled()//TODO: .withArguments(section_1)
	    expect(cell2.addSection).toHaveBeenCalled()//TODO: .withArguments(section_1)
	    expect(m.schedule_assignments[section_2().id]).toEqual({room_name: "room-2", timeslots: [1, 2], id: section_2().id})
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
	})

	afterEach(function() {
	    m.clearCell(m.getCell("room-2", 1))
	    m.clearCell(m.getCell("room-2", 2))
	})
	//TODO:  unscheduling classes
	//TODO:  what if the room or time is taken?
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
	    //TODO:  timeslots should be ordered chronologically
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

	//TODO:  what assertions should this actually make?
	it("should show already scheduled sections", function(){
	    table = m.el.children()[0]
	    expect(table.innerHTML).toMatch('S3188s1')
	})
    })
})
