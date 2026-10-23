const { generateFakeMatrix } = require("./FakeMatrix");
const { section_1, teacher_fixture } = require("./TestFixtures");

describe("Matrix", function(){
    var m;

    beforeEach(function(){
        m = generateFakeMatrix();
    });

    it("should have an element", function(){
        expect(m.el[0]).toBeInstanceOf(HTMLElement);
    });

    it("should have times, rooms, and sections", function(){
        expect(m.timeslots).toBeInstanceOf(Timeslots);
        expect(Object.keys(m.rooms)).toEqual(["101", "102", "103"]);
        expect(m.sections).toBeInstanceOf(Sections);
    });

    describe("highlightTimeslots", function() {
        it("adds the correct classes to the timeslots given for a single hour class", function() {
            m.highlightTimeslots([[5], [3]], m.sections.getById(2));
            expect(m.getCell(101, 5).el.hasClass("teacher-available-cell")).toBe(true);
            expect(m.getCell(101, 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(102, 5).el.hasClass("teacher-available-cell")).toBe(true);
            expect(m.getCell(102, 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(103, 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(101, 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(101, 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(102, 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(102, 3).el.hasClass("teacher-teaching-cell")).toBe(true);

            expect(m.getCell(103, 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 3).el.hasClass("teacher-teaching-cell")).toBe(true);

            expect(m.getCell(101, 7).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 11).el.hasClass("teacher-teaching-cell")).toBe(false);
        })

        it("marks the cells of the teachers' other sections", function() {
            m.highlightTimeslots([[5], [3]], m.sections.getById(2));
            expect(m.getCell(101, 3).el.hasClass("teacher-is-teaching-this-cell")).toBe(true);
        });

        it("adds a striped gradient for cells that are available, but can't be clicked", function() {
            m.highlightTimeslots([[11, 13], []], m.sections.getById(3));
            expect(m.getCell(103, 11).el.hasClass("teacher-available-cell")).toBe(true);
            expect(m.getCell(103, 13).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 13).el.hasClass("teacher-available-not-first-cell")).toBe(true);
        });
    });

    describe("unhighlightTimeslots", function() {
        it("removes the correct classes from the timeslots given", function() {
            m.highlightTimeslots([[5], [3]], m.sections.getById(2));
            m.unhighlightTimeslots([[5], [3]]);

            expect(m.getCell(101, 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(101, 3).el.hasClass("teacher-teaching-cell")).toBe(false);
            expect(m.getCell(101, 3).el.hasClass("teacher-is-teaching-this-cell")).toBe(false);

            expect(m.getCell(102, 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(102, 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(103, 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(101, 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(101, 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(102, 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(102, 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(103, 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell(101, 7).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell(103, 11).el.hasClass("teacher-teaching-cell")).toBe(false);
        });
        it("removes the striped gradient too", function() {
            m.highlightTimeslots([[11, 13], []], m.sections.getById(3));
            m.unhighlightTimeslots([[11, 13], []]);

            expect(m.getCell(103, 13).el.hasClass("teacher-available-not-first-cell")).toBe(false);
        });
    });

    describe("getCell", function(){
        it("returns the html cell for the requested room and time", function(){
            var s1 = section_1();
            s1.teacher_data = [teacher_fixture()[1], teacher_fixture()[2]];
            s1.moderator_data = [];
            s1.schedulingComment = '';
            s1.schedulingLocked = false;
            expect(m.getCell(101, 3).section).toEqual(s1);
            // Cells take their room ids from the keys of the rooms object
            expect(m.getCell(101, 3).room_id).toEqual("101");
            expect(m.getCell(103, 3).timeslot_id).toEqual(3);

            expect(m.getCell(101, 11).room_id).toEqual("101");
            expect(m.getCell(101, 11).timeslot_id).toEqual(11);

            expect(m.getCell(102, 7).room_id).toEqual("102");
            expect(m.getCell(103, 7).timeslot_id).toEqual(7);

            expect(m.getCell(102, 5).section).toBeNull();
            expect(m.getCell(102, 5).room_id).toEqual("102");
            expect(m.getCell(101, 5).timeslot_id).toEqual(5);
        });
    });


    describe("when a room doesn't exist for some times", function(){
        it("should have disabled cells around it", function(){
            expect(m.getCell(102, 11).disabled).toBe(false);
            expect(m.getCell(101, 11).disabled).toBe(true);
            expect(m.getCell(101, 3).disabled).toBe(false);
            expect(m.getCell(102, 3).disabled).toBe(false);
        });

    });

    describe("validateAssignment", function(){
        describe("when a class is already scheduled in a room", function(){
            beforeEach(function(){
                m.sections.scheduleSection(m.sections.getById(2), 101, 5);
            });

            it("returns false", function(){
                var validObj = m.validateAssignment(m.sections.getById(3), 101, [3,5]);
                expect(validObj.valid).toEqual(false);
                expect(validObj.reason).toEqual("Error: There is already a class scheduled in Room 101 during timeslot 1");
            });
        });

        describe("when the assignment is valid", function(){
            it("returns true", function(){
                expect(m.validateAssignment(m.sections.getById(3), 103, [11, 13]).valid).toEqual(true);
            });
        });

        describe("when the timeslots are null", function(){
            it("returns false", function(){
                var validObj = m.validateAssignment(m.sections.getById(3), 102, null)
                expect(validObj.valid).toEqual(false);
                expect(validObj.reason).toEqual('Error: Not scheduled during a timeblock');
                });
        });

        describe("when the room is not available", function(){
            it("returns false", function(){
                var validObj = m.validateAssignment(m.sections.getById(3), 101, [11, 13]);
                expect(validObj.valid).toEqual(false);
                expect(validObj.reason).toEqual("Error: Room 101 is not available during timeslot 4");
            });
        });

        describe("when the teachers are not available", function(){
            it("returns false", function(){
                var validObj = m.validateAssignment(m.sections.getById(3), 102, [3, 5]);
                expect(validObj.valid).toEqual(false);
                expect(validObj.reason).toEqual("Error: The teachers of A22s1 are not available during timeslot 1");
            });
        });
    });

    describe("render", function(){
        it("should have a row for each room", function(){
            expect(m.getTable().rows.length).toEqual(4);
            // rooms are sorted by name
            expect(m.getTable().rows[1].cells[0].innerHTML).toMatch("Room 101");
            expect(m.getTable().rows[2].cells[0].innerHTML).toMatch("Room 102");
        })

        it("should have a column each timeslot", function(){
            var header = m.getTable().tHead;
            expect(header).toBeInstanceOf(HTMLElement);
            var headers = header.rows[0].cells;
            expect(headers.length).toEqual(6);
            //the corner block holds the print and legend buttons
            expect(headers[0].innerHTML).toMatch("Print Matrix");
            expect(headers[1].innerHTML).toMatch("first timeslot");
            expect(headers[2].innerHTML).toMatch("second timeslot");
        });

        it("should have a cell for every timeslot/room combination", function(){
            expect(m.getTable().rows[1].cells[1]).toBeDefined();
            expect(m.getTable().rows[1].cells[2]).toBeDefined();
            expect(m.getTable().rows[2].cells[1]).toBeDefined();
            expect(m.getTable().rows[2].cells[2]).toBeDefined();
        });

        it("should show already scheduled sections", function(){
            expect(m.el[0].innerHTML).toMatch('S11s1');
        });
    });

});
