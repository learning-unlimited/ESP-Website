describe("Matrix", function(){
    beforeEach(function(){
	m = new Matrix(time_fixture, room_fixture, schedule_assignments_fixture, sections_fixture, $j("<div/>"))
    })

    it("should have an element", function(){
	//TODO:  maybe we should assert that this is a jquery object?
	expect(m.el[0]).toBeHtmlNode()
    })

    it("should have times and rooms", function(){
	expect(m.timeslots).toBeObject()
	expect(m.rooms).toBeObject()
	expect(m.schedule_assigments).toBeObject()
	expect(m.sections).toBeObject()
    })

    describe("getCell", function(){
	it("returns the html cell for the requested room and time", function(){
	    expect(m.getCell("room-1", 1).section).toEqual(section_1)
	    expect(m.getCell("room-1", 2).section).toEqual(section_1)
	    expect(m.getCell("room-2", 1).innerHTML).toEqual(null)
	    expect(m.getCell("room-2", 2).innerHTML).toEqual(null)
	})
    })
    
    /*describe("scheduling", function(){
	beforeEach(function(){
	    //TODO:  unschedule all classes
	    //m.scheduleClass()
	})

	it("inserts the class into the matrix", function(){
	    //cells = [m.getCell("room-2", 1), m.getCell("room-2", 2)]
	    /*$j(cells).each(function(cell){
		spyOn(c, 'addSection')
	        expect(c.addSection).toHaveBeenCalled()//TODO:  with arguments
	    })
	    expect(m.scheduleClass(section_2, "room-2", [1,2])).toBeTrue()
	})

	it("should have draggable cells", function(){
	    //I guess just expect draggable to be called here?
	    //cells should be droppable
	})
	//TODO:  unscheduling classes
	//TODO:  what if the room or time is taken?
    })*/

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
