describe("Matrix", function(){
    var m;

    beforeEach(function(){
	    m = matrix_fixture();
    });

    it("should have an element and a garbage element", function(){
        expect(m.el[0]).toBeHtmlNode();
    });

    it("should have times, rooms, teachers, and schedule assignments", function(){
	    expect(m.timeslots).toBeObject();
	    expect(m.rooms).toBeObject();
	    expect(m.sections).toBeObject();
    });

    describe("getCell", function(){
	    it("returns the html cell for the requested room and time", function(){
            var s1 = section_1();
            s1.teacher_data = [teacher_fixture()[1], teacher_fixture()[2]];
	        expect(m.getCell("room-1", 1).section).toEqual(s1);
	        expect(m.getCell("room-1", 1).room_name).toEqual("room-1");
	        expect(m.getCell("room-1", 1).timeslot_id).toEqual(1);

	        expect(m.getCell("room-1", 2).section).toEqual(s1);
	        expect(m.getCell("room-1", 2).room_name).toEqual("room-1");
	        expect(m.getCell("room-1", 2).timeslot_id).toEqual(2);

            console.log(m);
	        expect(m.getCell("room-2", 1).innerHTML).toEqual(null);
	        expect(m.getCell("room-2", 1).room_name).toEqual("room-2");
	        expect(m.getCell("room-1", 1).timeslot_id).toEqual(1);

	        expect(m.getCell("room-2", 2).innerHTML).toEqual(null);
	        expect(m.getCell("room-2", 2).room_name).toEqual("room-2");
	        expect(m.getCell("room-1", 2).timeslot_id).toEqual(2);
	    });
    });


    describe("when a room doesn't exist for some times", function(){
	beforeEach(function(){
        m = matrix_fixture();
	})

	it("should have disabled cells around it", function(){
	    expect(m.getCell("room-1", 1).disabled).toBeFalse();
	    expect(m.getCell("room-2", 1).disabled).toBeTrue();
	    expect(m.getCell("room-1", 2).disabled).toBeFalse();
	    expect(m.getCell("room-2", 2).disabled).toBeFalse();
	});

    });

    describe("validateAssignment", function(){
	describe("when a class is already scheduled in a room", function(){
	    beforeEach(function(){
		    m.sections.scheduleSection(section_1(), "room-2", 2);
	    });
	    
	    it("returns false", function(){
		    var validObj = m.validateAssignment(section_2(), "room-2", [1,2]);
		    expect(validObj.valid).toEqual(false);
            expect(validObj.reason).toEqual("Error: timeslotundefined already has a class in room-2.");
	    }); 
	});

	describe("when the assignment is valid", function(){
	    it("returns true", function(){
		    expect(m.validateAssignment(section_2(), "room-2", [1,2]).valid).toEqual(true);
	    });
	});

	describe("when the timeslots are null", function(){
	    it("returns false", function(){
            var validObj = m.validateAssignment(section_2(), "room-2", null)
		    expect(validObj.valid).toEqual(false);
            expect(validObj.reason).toEqual('Error: Not scheduled during a timeblock');
	    });
	});
    });

    describe("render", function(){
	beforeEach(function(){
	    m.render();
	})

	it("should have a row for each room", function(){
 	    expect(m.el.children().length).toEqual(1);
	    var table = m.el.children()[0];
	    expect(table.rows.length).toEqual(3);
	    //TODO:  ordering should probably be deterministic, but I'm not sure how
	    expect(table.rows[1].cells[0].innerHTML).toMatch("room-1");
	    expect(table.rows[2].cells[0].innerHTML).toMatch("room-2");
	})

	it("should have a column each timeslot", function(){
	    var table = m.el.children()[0];
	    
	    var header = table.tHead;
	    expect(header).toBeHtmlNode();
	    headers = header.rows[0].cells;
	    expect(headers.length).toEqual(3);
	    //the corner block should be empty
	    expect(headers[1].innerHTML).toMatch("first timeslot");
	    expect(headers[2].innerHTML).toMatch("second timeslot");
	});

	it("should have a cell for every timeslot/room combination", function(){
	    var table = m.el.children()[0];
	    expect(table.rows[1].cells[1]).toBeDefined();
	    expect(table.rows[1].cells[2]).toBeDefined();
	    expect(table.rows[2].cells[1]).toBeDefined();
	    expect(table.rows[2].cells[2]).toBeDefined();
	});

	it("should show already scheduled sections", function(){
	    var table = m.el.children()[0];
	    expect(table.innerHTML).toMatch('S3188s1');
	});
    });
});
