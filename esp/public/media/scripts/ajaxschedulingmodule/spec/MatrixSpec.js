describe("Matrix", function(){
    var m;

    beforeEach(function(){
	m = new Matrix(
	    time_fixture(),
	    room_fixture(),
        teacher_fixture(),
	    schedule_assignments_fixture(),
	    sections_fixture(),
	    $j("<div/>"), $j("<div/>"), $j("<div/>"), $j("<div/>"),
	    new FakeApiClient());
    });

    it("should have an element and a garbage element", function(){
	expect(m.el[0]).toBeHtmlNode();
	expect(m.garbage_el[0]).toBeHtmlNode();
    });

    it("should have times, rooms, teachers, and schedule assignments", function(){
	    expect(m.timeslots).toBeObject();
	    expect(m.rooms).toBeObject();
        expect(m.teachers).toBeObject();
	    expect(m.schedule_assignments).toBeObject();
	    expect(m.sections).toBeObject();
    });

    describe("getCell", function(){
	    it("returns the html cell for the requested room and time", function(){
	        expect(m.getCell("room-1", 1).section).toEqual(section_1());
	        expect(m.getCell("room-1", 1).room_name).toEqual("room-1");
	        expect(m.getCell("room-1", 1).timeslot_id).toEqual(1);

	        expect(m.getCell("room-1", 2).section).toEqual(section_1());
	        expect(m.getCell("room-1", 2).room_name).toEqual("room-1");
	        expect(m.getCell("room-1", 2).timeslot_id).toEqual(2);

	        expect(m.getCell("room-2", 1).innerHTML).toEqual(null);
	        expect(m.getCell("room-2", 1).room_name).toEqual("room-2");
	        expect(m.getCell("room-1", 1).timeslot_id).toEqual(1);

	        expect(m.getCell("room-2", 2).innerHTML).toEqual(null);
	        expect(m.getCell("room-2", 2).room_name).toEqual("room-2");
	        expect(m.getCell("room-1", 2).timeslot_id).toEqual(2);
	    });
    });

    describe("getAvailableTimeslotsForSection", function() {
        it("returns the rooms where all teachers have availability", function() {
            section1 = m.sections[3329];
            timeslots1 = m.getAvailableTimeslotsForSection(section1);
            // Test available timeslots
            expect(timeslots1[0].length).toEqual(1);
            expect(timeslots1[0][0]).toEqual(1);

            // Test timeslots while teaching
            expect(timeslots1[1].length).toEqual(0);

            section2 = m.sections[3538];
            timeslots2 = m.getAvailableTimeslotsForSection(section2);
            expect(timeslots2[0].length).toEqual(2);

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
		    m.scheduleSection(section_1().id, "room-2", 2);
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

    describe("scheduleSection", function(){
	describe("when validations return true", function(){
	    it("calls out to the api", function() {
		spyOn(m.api_client, 'schedule_section');
		spyOn(m, 'validateAssignment').andReturn({valid: true});
		m.scheduleSection(section_1().id, "room-2", 1);
		expect(m.api_client.schedule_section).toHaveBeenCalled();
		
		var args = m.api_client.schedule_section.argsForCall[0];
		expect(args[0]).toEqual(section_1().id);
		expect(args[1]).toEqual([1]);
		expect(args[2]).toEqual("room-2");
	    });
	});

	describe("when validations return false", function(){
	    it("calls out to the api", function() {
		spyOn(m.api_client, 'schedule_section');
		spyOn(m, 'validateAssignment').andReturn(false);
		m.scheduleSection(section_2().id, "room-2", 1);
		expect(m.api_client.schedule_section).not.toHaveBeenCalled();
	    });
	});
    });

    describe("unscheduleSection", function(){
	it("calls out to the api", function() {
	    spyOn(m.api_client, 'unschedule_section');
	    m.unscheduleSection(section_2().id);
	    expect(m.api_client.unschedule_section).toHaveBeenCalled();
	    
	    var args = m.api_client.unschedule_section.argsForCall[0];
	    expect(args[0]).toEqual(section_2().id);
	});
    });

    
    describe("scheduleSectionLocal", function(){
	it("inserts the class into the matrix", function(){
	    var cell1 = m.getCell("room-2", 1);
	    var cell2 = m.getCell("room-2", 2);
	    spyOn(cell1, 'addSection');
	    spyOn(cell2, 'addSection');
	    m.scheduleSectionLocal(section_2().id, "room-2", [1,2]);
	    expect(cell1.addSection).toHaveBeenCalledWith(section_2());
	    expect(cell2.addSection).toHaveBeenCalledWith(section_2());
	    expect(m.schedule_assignments[section_2().id]).toEqual({room_name: "room-2", timeslots: [1, 2], id: section_2().id});
	});

	it("unschedules the class from the old location", function(){
	    var cell1 = m.getCell("room-1", 1);
	    var cell2 = m.getCell("room-1", 2);
	    spyOn(cell1, 'removeSection');
	    spyOn(cell2, 'removeSection');
	    m.scheduleSectionLocal(section_1().id, "room-2", [1,2]);
	    expect(cell1.removeSection).toHaveBeenCalled();
	    expect(cell2.removeSection).toHaveBeenCalled();
	    expect(m.schedule_assignments[section_1().id]).toEqual({room_name: "room-2", timeslots: [1, 2], id: section_1().id});
	});

	describe("when the class is already scheduled in the same spot", function(){
	    beforeEach(function(){
		m.scheduleSectionLocal(section_2().id, "room-2", [1,2]);
	    })

	    it("doesn't change anything when the assignment is the same as the old one", function(){
		m.scheduleSectionLocal(section_2().id, "room-2", [1,2]);

		expect(m.getCell("room-2", 1).section).toEqual(section_2());
	    })
	})

	it("fires a schedule-changed event", function(){
	    var event_fired = false;
	    $j("body").on("schedule-changed", function(){
		event_fired = true;
	    })
	    m.scheduleSection(section_2().id, "room-2", 1);
	    expect(event_fired).toBeTrue();
	});

	afterEach(function() {
	    m.clearCell(m.getCell("room-2", 1));
	    m.clearCell(m.getCell("room-2", 2));
	});
    });

    describe("unscheduleSectionLocal", function(){
	it("removes the class from the matrix", function(){
	    m.scheduleSection(section_2().id, "room-2", 1);

	    expect(m.getCell("room-2", 1).section).toEqual(section_2());
	    expect(m.getCell("room-2", 2).section).toEqual(section_2());
	    m.unscheduleSectionLocal(section_2().id);
	    expect(m.getCell("room-2", 1).section).not.toEqual(section_2());
	    expect(m.getCell("room-2", 2).section).not.toEqual(section_2());
	});

	it("fires a schedule-changed event", function(){
	    var event_fired = false;
	    $j("body").on("schedule-changed", function(){
		event_fired = true;
	    })
	    m.unscheduleSectionLocal(section_1().id);
	    expect(event_fired).toBeTrue();
	});

	it("modifies the schedule_assignments data structure", function(){
	    expect(m.schedule_assignments[section_1().id]).toEqual({room_name: "room-1", timeslots: [1,2], id: section_1().id});
	    m.unscheduleSectionLocal(section_1().id);
	    expect(m.schedule_assignments[section_1().id]).toEqual({room_name: null, timeslots: [], id: section_1().id});
	});
    });

    describe("clearCell", function(){
	it("removes a section from that cell", function(){
	    var cell = m.getCell("room-1", 1);
	    spyOn(cell, "removeSection");
	    expect(cell.section).not.toBeNull();
	    m.clearCell(m.getCell("room-1", 1));
	    expect(cell.removeSection).toHaveBeenCalled();
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
