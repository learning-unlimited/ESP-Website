const { generateFakeMatrix } = require("./FakeMatrix");
const { section_fixture, teacher_fixture } = require("./TestFixtures");

describe("SectionsSpec", function() {
    var sections, matrix;

    beforeEach(function() {
        matrix = generateFakeMatrix();
        sections = matrix.sections;
    });

    it("adds teacher_data property to each section", function() {
        var teachers = teacher_fixture();
        var section1 = sections.getById(1);
        expect(section1.teacher_data).toEqual([teachers[1], teachers[2]]);
    });

    describe("bindMatrix", function() {
        it("adds the property matrix to the sections object", function() {
            sections.matrix = null;
            sections.bindMatrix(matrix);
            expect(sections.matrix).toBe(matrix);
        });
    });
    describe("getById", function() {
        it("gets the correct section", function() {
            var s = section_fixture()[1];
            s.teacher_data = [teacher_fixture()[1], teacher_fixture()[2]]
            s.moderator_data = [];
            s.schedulingComment = '';
            s.schedulingLocked = false;
            expect(sections.getById(1)).toEqual(s);
        });
    });

    describe("filtered_sections", function() {
        it("returns the unscheduled sections", function() {
            var unscheduledSections = sections.filtered_sections();
            expect(unscheduledSections).toEqual([sections.getById(2), sections.getById(4),
                                                 sections.getById(5), sections.getById(6)]);
        });
    });

    describe("selectSection", function() {
        it("selects all cells that hold the section", function() {
            var cell1 = matrix.getCell(102, 11);
            var cell2 = matrix.getCell(102, 13);
            jest.spyOn(cell1, "select").mockImplementation(function(){});
            jest.spyOn(cell2, "select").mockImplementation(function(){});
            sections.selectSection(sections.getById(3));
            expect(cell1.select).toHaveBeenCalled();
            expect(cell2.select).toHaveBeenCalled();
        });

        it("highlights the available cells", function() {
            jest.spyOn(matrix, "highlightTimeslots").mockImplementation(function(){});
            sections.selectSection(sections.getById(3));
            expect(matrix.highlightTimeslots).toHaveBeenCalled();
        });

        it("displays the section's information on the panel", function() {
            jest.spyOn(matrix.sectionInfoPanel, "displaySection").mockImplementation(function(){});
            sections.selectSection(sections.getById(3));
            expect(matrix.sectionInfoPanel.displaySection).toHaveBeenCalled();
        });

    });

    describe("unselectSection", function() {
        beforeEach(function() {
            sections.selectSection(sections.getById(3));
        });

        it("unselects all cells that hold the section", function() {
            var cell1 = matrix.getCell(102, 11);
            var cell2 = matrix.getCell(102, 13);
            jest.spyOn(cell1, "unselect").mockImplementation(function(){});
            jest.spyOn(cell2, "unselect").mockImplementation(function(){});
            sections.unselectSection();
            expect(cell1.unselect).toHaveBeenCalled();
            expect(cell2.unselect).toHaveBeenCalled();
        });

        it("unhighlights the available cells", function() {
            jest.spyOn(matrix, "unhighlightTimeslots").mockImplementation(function(){});
            sections.unselectSection();
            expect(matrix.unhighlightTimeslots).toHaveBeenCalled();
        });

        it("hides the section information panel", function() {
            jest.spyOn(matrix.sectionInfoPanel, "hide").mockImplementation(function(){});
            sections.unselectSection();
            expect(matrix.sectionInfoPanel.hide).toHaveBeenCalled();

        });

    });

    describe("getAvailableTimeslots", function() {
        it("gets the timeslots available for the section", function() {
            expect(sections.getAvailableTimeslots(sections.getById(2))).toEqual([[5], [3, 3]]);
        });

        it("ignores teacher availability when overridden", function() {
            matrix.sectionInfoPanel.override = true;
            expect(sections.getAvailableTimeslots(sections.getById(2))[0].sort()).toEqual([3, 5, 7, 11, 13].sort());
        });
    });

    describe("getTeachersString", function() {
        it("gets all teachers for the section separated by a comma", function() {
            expect(sections.getTeachersString(sections.getById(1))).toEqual("Alyssa P. Hacker, Ben Bitdiddle");
        });

    });


    describe("scheduleSection", function(){
        describe("when validations return true", function(){
            it("calls out to the api", function() {
                jest.spyOn(sections.apiClient, 'schedule_section').mockImplementation(function(){});
                jest.spyOn(matrix, 'validateAssignment').mockReturnValue({valid: true});
                sections.scheduleSection(sections.getById(2), 102, 5);
                expect(sections.apiClient.schedule_section).toHaveBeenCalled();

                var args = sections.apiClient.schedule_section.mock.calls[0];
                expect(args[0]).toEqual(2);
                expect(args[1]).toEqual([5]);
                expect(args[2]).toEqual(102);
                expect(args[3]).toEqual(false);
            });
        });

        describe("when validations return false", function(){
            it("doesn't call out to the api", function() {
                jest.spyOn(sections.apiClient, 'schedule_section').mockImplementation(function(){});
                jest.spyOn(matrix, 'validateAssignment').mockReturnValue({valid: false, reason: "invalid"});
                sections.scheduleSection(sections.getById(2), 102, 3);
                expect(sections.apiClient.schedule_section).not.toHaveBeenCalled();
            });
        });

        describe("when the section is locked", function(){
            it("doesn't call out to the api", function() {
                jest.spyOn(sections.apiClient, 'schedule_section').mockImplementation(function(){});
                jest.spyOn(matrix.messagePanel, 'addMessage').mockImplementation(function(){});
                sections.getById(2).schedulingLocked = true;
                sections.scheduleSection(sections.getById(2), 102, 5);
                expect(sections.apiClient.schedule_section).not.toHaveBeenCalled();
                expect(matrix.messagePanel.addMessage).toHaveBeenCalled();
            });
        });

        describe("when the server reports an error", function(){
            it("puts the section back where it was", function() {
                jest.spyOn(sections.apiClient, 'schedule_section').mockImplementation(
                    function(section_id, timeslot_ids, room_id, override, callback, errorReporter){
                        errorReporter("The teacher is not available");
                    });
                jest.spyOn(matrix.messagePanel, 'addMessage').mockImplementation(function(){});
                jest.spyOn(console, 'log').mockImplementation(function(){});
                sections.scheduleSection(sections.getById(1), 102, 5);
                expect(matrix.getCell(101, 3).section).toBe(sections.getById(1));
                expect(matrix.getCell(102, 5).section).toBeNull();
                expect(matrix.messagePanel.addMessage).toHaveBeenCalledWith("Error: The teacher is not available", "error");
            });
        });
    });

    describe("unscheduleSection", function(){
        it("calls out to the api", function() {
            jest.spyOn(sections.apiClient, 'unschedule_section').mockImplementation(function(){});
            sections.unscheduleSection(sections.getById(2));
            expect(sections.apiClient.unschedule_section).toHaveBeenCalled();

            var args = sections.apiClient.unschedule_section.mock.calls[0];
            expect(args[0]).toEqual(2);
        });
    });


    describe("scheduleSectionLocal", function(){
        it("inserts the class into the matrix", function(){
            var cell1 = matrix.getCell(102, 5);
            var cell2 = matrix.getCell(102, 3);
            jest.spyOn(cell1, 'addSection').mockImplementation(function(){});
            jest.spyOn(cell2, 'addSection').mockImplementation(function(){});
            sections.scheduleSectionLocal(sections.getById(2), 102, [5]);
            expect(cell1.addSection).toHaveBeenCalledWith(sections.getById(2));
            expect(cell2.addSection).not.toHaveBeenCalledWith(sections.getById(2));
            expect(sections.scheduleAssignments[2]).toEqual({room_id: 102, timeslots: [5], id: 2});
        });

        it("unschedules the class from the old location", function(){
            var cell = matrix.getCell(101, 3);
            jest.spyOn(cell, 'removeSection').mockImplementation(function(){});
            sections.scheduleSectionLocal(sections.getById(1), 102, [5]);
            expect(cell.removeSection).toHaveBeenCalled();
            expect(sections.scheduleAssignments[1]).toEqual({room_id: 102, timeslots: [5], id: 1});
        });

        describe("when the class is already scheduled in the same spot", function(){
            beforeEach(function(){
                sections.scheduleSectionLocal(sections.getById(1), 101, [3]);
            })

            it("doesn't change anything when the assignment is the same as the old one", function(){
                expect(matrix.getCell(101, 3).section).toBe(sections.getById(1));
            })
        })

        it("fires a schedule-changed event", function(){
            var event_fired = false;
            $j("body").on("schedule-changed", function(){
                event_fired = true;
            })
            sections.scheduleSection(sections.getById(3), 103, 11);
            expect(event_fired).toBe(true);
        });
    });

    describe("unscheduleSectionLocal", function(){
        it("removes the class from the matrix", function(){
            sections.unscheduleSectionLocal(sections.getById(1));
            expect(matrix.getCell(101, 3).section).toBeNull();
        });

        it("fires a schedule-changed event", function(){
            var event_fired = false;
            $j("body").on("schedule-changed", function(){
                event_fired = true;
            })
            sections.unscheduleSectionLocal(sections.getById(1));
            expect(event_fired).toBe(true);
        });

        it("modifies the schedule_assignments data structure", function(){
            expect(sections.scheduleAssignments[1]).toEqual({room_id: 101, timeslots: [3], id: 1});
            sections.unscheduleSectionLocal(sections.getById(1));
            expect(sections.scheduleAssignments[1]).toEqual({room_id: null, timeslots: [], id: 1});
        });
    });


    describe("scheduleAsGhost", function() {
        it("displays the section as a ghost", function() {
            var section = sections.getById(3);
            sections.selectSection(section);
            sections.scheduleAsGhost(103, 11);
            expect(matrix.getCell(103, 11).el.hasClass("ghost-section")).toBe(true);
            expect(matrix.getCell(103, 13).el.hasClass("ghost-section")).toBe(true);
        });

    });

    describe("unscheduleAsGhost", function() {
        it("removes section from all cells", function() {
            var section = sections.getById(3);
            sections.selectSection(section);
            sections.scheduleAsGhost(103, 11);
            sections.unscheduleAsGhost();
            expect(matrix.getCell(103, 11).el.hasClass("ghost-section")).toBe(false);
            expect(matrix.getCell(103, 13).el.hasClass("ghost-section")).toBe(false);
            expect(sections.ghostScheduleAssignment).toEqual({});
        });
    });
});
