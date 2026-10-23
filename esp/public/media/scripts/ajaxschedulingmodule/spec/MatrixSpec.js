describe("Matrix", function(){
    var m;

    beforeEach(function(){
        m = generateFakeMatrix();
    });

    it("should have an element", function(){
        expect(m.el[0]).toBeHtmlNode();
    });

    it("should have times, rooms, teachers, and schedule assignments", function(){
        expect(m.timeslots).toBeObject();
        expect(m.rooms).toBeObject();
        expect(m.sections).toBeObject();
    });

    describe("highlightTimeslots", function() {
        it("adds the correct classes to the timeslots given for a single hour class", function() {
            m.highlightTimeslots([[5], [3]], m.sections.getById(2));
            expect(m.getCell("room-1", 5).el.hasClass("teacher-available-cell")).toBe(true);
            expect(m.getCell("room-1", 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-2", 5).el.hasClass("teacher-available-cell")).toBe(true);
            expect(m.getCell("room-2", 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-3", 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-3", 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-1", 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-1", 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-2", 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-2", 3).el.hasClass("teacher-teaching-cell")).toBe(true);

            expect(m.getCell("room-3", 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-3", 3).el.hasClass("teacher-teaching-cell")).toBe(true);

            expect(m.getCell("room-1", 7).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-3", 11).el.hasClass("teacher-teaching-cell")).toBe(false);
        })

        it("adds a striped gradient for cells that are available, but can't be clicked", function() {
            m.highlightTimeslots([[11, 13], []], m.sections.getById(3));
            expect(m.getCell("room-3", 13).el.hasClass("teacher-available-not-first-cell")).toBeTrue();
        });
    });

    describe("unhighlightTimeslots", function() {
        it("removes the correct classes from the timeslots given", function() {
            m.highlightTimeslots([[5], [3]], m.sections.getById(2));
            m.unhighlightTimeslots([[5], [3]]);

            expect(m.getCell("room-1", 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-1", 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-2", 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-2", 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-3", 3).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-3", 3).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-1", 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-1", 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-2", 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-2", 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-3", 5).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-3", 5).el.hasClass("teacher-teaching-cell")).toBe(false);

            expect(m.getCell("room-1", 7).el.hasClass("teacher-available-cell")).toBe(false);
            expect(m.getCell("room-3", 11).el.hasClass("teacher-teaching-cell")).toBe(false);
        });
        it("removes the striped gradient too", function() {
            m.highlightTimeslots([[11, 13], []], m.sections.getById(3));
            m.unhighlightTimeslots([[3, 5], []], m.sections.getById(3));

            expect(m.getCell("room-2", 5).el.hasClass("teacher-available-not-first-cell")).toBeFalse();
            expect(m.getCell("room-3", 3).el.hasClass("teacher-available-not-first-cell")).toBeFalse();
        });
    });

    describe("getCell", function(){
        it("returns the html cell for the requested room and time", function(){
            var s1 = section_1();
            s1.teacher_data = [teacher_fixture()[1], teacher_fixture()[2]];
            s1.schedulingComment = '';
            s1.schedulingLocked = false;
            expect(m.getCell("room-1", 3).section).toEqual(s1);
            expect(m.getCell("room-1", 3).room_name).toEqual("room-1");
            expect(m.getCell("room-3", 3).timeslot_id).toEqual(3);

            expect(m.getCell("room-1", 11).room_name).toEqual("room-1");
            expect(m.getCell("room-1", 11).timeslot_id).toEqual(11);

            expect(m.getCell("room-2", 7).innerHTML).toEqual(null);
            expect(m.getCell("room-2", 7).room_name).toEqual("room-2");
            expect(m.getCell("room-3", 7).timeslot_id).toEqual(7);

            expect(m.getCell("room-2", 5).innerHTML).toEqual(null);
            expect(m.getCell("room-2", 5).room_name).toEqual("room-2");
            expect(m.getCell("room-1", 5).timeslot_id).toEqual(5);
        });
    });


    describe("when a room doesn't exist for some times", function(){
        it("should have disabled cells around it", function(){
            expect(m.getCell("room-2", 11).disabled).toBeFalse();
            expect(m.getCell("room-1", 11).disabled).toBeTrue();
            expect(m.getCell("room-1", 3).disabled).toBeFalse();
            expect(m.getCell("room-2", 3).disabled).toBeFalse();
        });

    });

    describe("validateAssignment", function(){
        describe("when a class is already scheduled in a room", function(){
            beforeEach(function(){
                m.sections.scheduleSection(m.sections.getById(2), "room-1", 5);
            });

            it("returns false", function(){
                var validObj = m.validateAssignment(m.sections.getById(3), "room-1", [3,5]);
                expect(validObj.valid).toEqual(false);
                expect(validObj.reason).toEqual("Error: timeslot3 already has a class in room-1.");
            });
        });

        describe("when the assignment is valid", function(){
            it("returns true", function(){
                expect(m.validateAssignment(m.sections.getById(3), "room-3", [11, 13]).valid).toEqual(true);
            });
        });

        describe("when the timeslots are null", function(){
            it("returns false", function(){
                var validObj = m.validateAssignment(m.sections.getById(3), "room-2", null)
                expect(validObj.valid).toEqual(false);
                expect(validObj.reason).toEqual('Error: Not scheduled during a timeblock');
                });
        });
    });

    describe("render", function(){
        it("should have a row for each room", function(){
            expect(m.el.children().length).toEqual(1);
            var table = m.el.children()[0];
            expect(m.getTable().rows.length).toEqual(4);
            //TODO:  ordering should probably be deterministic, but I'm not sure how
            expect(m.getTable().rows[1].cells[0].innerHTML).toMatch("room-1");
            expect(m.getTable().rows[2].cells[0].innerHTML).toMatch("room-2");
        })

        it("should have a column each timeslot", function(){
            var table = m.el.children()[0];

            var header = m.getTable().tHead;
            expect(header).toBeHtmlNode();
            headers = header.rows[0].cells;
            expect(headers.length).toEqual(6);
            //the corner block should be empty
            expect(headers[1].innerHTML).toMatch("first timeslot");
            expect(headers[2].innerHTML).toMatch("second timeslot");
        });

        it("should have a cell for every timeslot/room combination", function(){
            var table = m.el.children()[0];
            expect(m.getTable().rows[1].cells[1]).toBeDefined();
            expect(m.getTable().rows[1].cells[2]).toBeDefined();
            expect(m.getTable().rows[2].cells[1]).toBeDefined();
            expect(m.getTable().rows[2].cells[2]).toBeDefined();
        });

        it("should show already scheduled sections", function(){
            var table = m.el.children()[0];
            expect(table.innerHTML).toMatch('S11s1');
        });
    });

});

describe("Matrix room filter scoring", function() {
    var filter, weights;
    var room = {id: 1, text: "10-250", num_students: 20, resource_lines: ["Projector"]};

    beforeEach(function() {
        weights = {capacity: {val: 1}, resource: {val: 1}};
        filter = {
            roomCapacityMin: {active: false, weight: "capacity", penalty: function(a) {
                return a.num_students >= 25 ? 0 : Matrix.capacityPenalty(a.num_students, 25);
            }},
            roomResource: {active: false, weight: "resource", valid: function(a) {
                return a.resource_lines.indexOf("Whiteboard") > -1;
            }},
        };
    });

    describe("capacityPenalty", function() {
        it("is the squared normalized distance from the limit", function() {
            expect(Matrix.capacityPenalty(20, 25)).toBeCloseTo(0.04);
            expect(Matrix.capacityPenalty(30, 25)).toBeCloseTo(0.04);
        });

        it("is capped at 1", function() {
            expect(Matrix.capacityPenalty(100, 25)).toBe(1);
        });

        it("is 1 for a limit of 0", function() {
            expect(Matrix.capacityPenalty(10, 0)).toBe(1);
        });
    });

    describe("roomMatchScore", function() {
        it("is 1 when no filters are active", function() {
            expect(Matrix.roomMatchScore(room, filter, weights)).toBe(1);
        });

        it("averages the active filter penalties", function() {
            filter.roomCapacityMin.active = true;
            filter.roomResource.active = true;
            expect(Matrix.roomMatchScore(room, filter, weights)).toBeCloseTo(1 - (0.04 + 1) / 2);
        });

        it("weights the active filter penalties", function() {
            filter.roomCapacityMin.active = true;
            filter.roomResource.active = true;
            weights.resource.val = 3;
            expect(Matrix.roomMatchScore(room, filter, weights)).toBeCloseTo(1 - (0.04 + 3) / 4);
        });

        it("ignores filters with a weight of 0", function() {
            filter.roomCapacityMin.active = true;
            filter.roomResource.active = true;
            weights.resource.val = 0;
            expect(Matrix.roomMatchScore(room, filter, weights)).toBeCloseTo(0.96);
        });
    });

    describe("compareRoomNames", function() {
        it("sorts room numbers numerically", function() {
            expect(Matrix.compareRoomNames({text: "10-250"}, {text: "2-105"})).toBeGreaterThan(0);
        });
    });
});
