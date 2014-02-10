describe("Matrix", function(){
    beforeEach(function(){
	m = new Matrix(time_fixture, room_fixture, schedule_assignments_fixture, sections_fixture, $j("<div/>")[0])
    })

    it("should have an element", function(){
	expect(m.el).toBeHtmlNode()
    })

    it("should have times and rooms", function(){
	expect(m.timeslots).toBeObject()
	expect(m.rooms).toBeObject()
	expect(m.schedule_assigments).toBeObject()
	expect(m.sections).toBeObject()
    })

    describe("render", function(){
	beforeEach(function(){
	    m.render()
	})

	it("should have a row for each room", function(){
 	    expect(m.el.children.length).toEqual(1)
	    table = m.el.children[0]
	    expect(table.rows.length).toEqual(3)
	    //TODO:  ordering should probably be deterministic, but I'm not sure how
	    expect(table.rows[1].cells[0].innerHTML).toMatch("room-1")
	    expect(table.rows[2].cells[0].innerHTML).toMatch("room-2")
	})

	it("should have a header with each timeslot", function(){
	    //TODO:  timeslots should be ordered chronologically
	    expect(m.el.children.length).toEqual(1)
	    table = m.el.children[0]
	    
	    header = table.tHead
	    expect(header).toBeHtmlNode()
	    headers = header.rows[0].cells
	    expect(headers.length).toEqual(3)
	    //the corner block should be empty
	    expect(headers[1].innerHTML).toMatch("first timeslot")
	    expect(headers[2].innerHTML).toMatch("second timeslot")
	})

	it("should have a cell for every timeslot/room combination", function(){
	    table = m.el.children[0]
	    expect(table.rows[1].cells[1]).toBeDefined()
	    expect(table.rows[1].cells[2]).toBeDefined()
	    expect(table.rows[2].cells[1]).toBeDefined()
	    expect(table.rows[2].cells[2]).toBeDefined()
	    
	})

	it("should show already scheduled sections", function(){
	    table = m.el.children[0]
	    expect(table.rows[1].cells[1].innerHTML).toMatch('S3188s1')
	    expect(table.rows[1].cells[2].innerHTML).toMatch('S3188s1')
	    //doesn't show the class we didn't schedule
	    expect(table.innerHTML).not.toMatch('M3343s1')
	})
    })
})
