describe("SectionsSpec", function() {
    var sections, matrix;

    beforeEach(function() {
        sections = new Sections(section_fixture(), {}, teacher_fixture(),
            schedule_assignment_fixture(), new FakeApiClient());
        matrix = generateFakeMatrix();
        sections.bindMatrix(matrix);
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
            expect(sections.matrix).toEqual(matrix);
        });
    });
    describe("getById", function() {
        it("gets the correct section", function() {
            var s = section_fixture()[1];
            s.teacher_data = [teacher_fixture()[1], teacher_fixture()[2]]
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
            var cell1 = matrix.getCell("room-2", 11);
            var cell2 = matrix.getCell("room-2", 13);
            spyOn(cell1, "select");
            spyOn(cell2, "select");
            sections.selectSection(sections.getById(3));
            expect(cell1.select).toHaveBeenCalled();
            expect(cell2.select).toHaveBeenCalled();
        });

        it("highlights the available cells", function() {
            spyOn(matrix, "highlightTimeslots");
            sections.selectSection(sections.getById(3));
            expect(matrix.highlightTimeslots).toHaveBeenCalled();
        });

        it("displays the section's information on the panel", function() {
            spyOn(matrix.sectionInfoPanel, "displaySection");
            sections.selectSection(sections.getById(3));
            expect(matrix.sectionInfoPanel.displaySection).toHaveBeenCalled();
        });

    });

    describe("unselectSection", function() {
        beforeEach(function() {
            sections.selectSection(sections.getById(3));
        });

        it("unselects all cells that hold the section", function() {
            var cell1 = matrix.getCell("room-2", 11);
            var cell2 = matrix.getCell("room-2", 13);
            spyOn(cell1, "unselect");
            spyOn(cell2, "unselect");
            sections.unselectSection(sections.getById(3));
            expect(cell1.unselect).toHaveBeenCalled();
            expect(cell2.unselect).toHaveBeenCalled();
        });

        it("unhighlights the available cells", function() {
            spyOn(matrix, "unhighlightTimeslots");
            sections.unselectSection(sections.getById(3));
            expect(matrix.unhighlightTimeslots).toHaveBeenCalled();
        });

        it("hides the section information panel", function() {
            spyOn(matrix.sectionInfoPanel, "hide");
            sections.unselectSection(sections.getById(3));
            expect(matrix.sectionInfoPanel.hide).toHaveBeenCalled();

        });

    });

    describe("getAvailableTimeslots", function() {
        it("gets the timeslots available for the section", function() {
            expect(sections.getAvailableTimeslots(sections.getById(2))).toEqual([[5], [3, 3]]);
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
                spyOn(sections.apiClient, 'schedule_section');
                spyOn(matrix, 'validateAssignment').andReturn({valid: true});
                sections.scheduleSection(sections.getById(2), "room-2", 5);
                expect(sections.apiClient.schedule_section).toHaveBeenCalled();

                var args = sections.apiClient.schedule_section.argsForCall[0];
                expect(args[0]).toEqual(2);
                expect(args[1]).toEqual([5]);
                expect(args[2]).toEqual("room-2");
            });
        });

        describe("when validations return false", function(){
            it("doesn't call out to the api", function() {
                spyOn(sections.apiClient, 'schedule_section');
                spyOn(matrix, 'validateAssignment').andReturn(false);
                sections.scheduleSection(sections.getById(2), "room-2", 3);
                expect(sections.apiClient.schedule_section).not.toHaveBeenCalled();
            });
        });
    });

    describe("unscheduleSection", function(){
        it("calls out to the api", function() {
            spyOn(sections.apiClient, 'unschedule_section');
            sections.unscheduleSection(sections.getById(2));
            expect(sections.apiClient.unschedule_section).toHaveBeenCalled();

            var args = sections.apiClient.unschedule_section.argsForCall[0];
            expect(args[0]).toEqual(2);
        });
    });


    describe("scheduleSectionLocal", function(){
        it("inserts the class into the matrix", function(){
            var cell1 = matrix.getCell("room-2", 5);
            var cell2 = matrix.getCell("room-2", 3);
            spyOn(cell1, 'addSection');
            spyOn(cell2, 'addSection');
            sections.scheduleSectionLocal(sections.getById(2), "room-2", [5]);
            expect(cell1.addSection).toHaveBeenCalledWith(sections.getById(2));
            expect(cell2.addSection).not.toHaveBeenCalledWith(sections.getById(2));
            expect(sections.scheduleAssignments[2]).toEqual({room_name: "room-2", timeslots: [5], id: 2});
        });

        it("unschedules the class from the old location", function(){
            var cell = matrix.getCell("room-1", 3);
            spyOn(cell, 'removeSection');
            sections.scheduleSectionLocal(sections.getById(1), "room-2", [5]);
            expect(cell.removeSection).toHaveBeenCalled();
            expect(sections.scheduleAssignments[1]).toEqual({room_name: "room-2", timeslots: [5], id: 1});
        });

        describe("when the class is already scheduled in the same spot", function(){
            beforeEach(function(){
                sections.scheduleSectionLocal(sections.getById(1), "room-1", [3]);
            })

            it("doesn't change anything when the assignment is the same as the old one", function(){
                expect(matrix.getCell("room-1", 3).section).toEqual(sections.getById(1));
            })
        })

        it("fires a schedule-changed event", function(){
            var event_fired = false;
            $j("body").on("schedule-changed", function(){
                event_fired = true;
            })
            sections.scheduleSection(sections.getById(3), "room-3", 11);
            expect(event_fired).toBeTrue();
        });

        afterEach(function() {
            matrix.getCell("room-2", 3).removeSection();
            matrix.getCell("room-2", 5).removeSection();
        });
    });

    describe("unscheduleSectionLocal", function(){
        it("removes the class from the matrix", function(){
            sections.unscheduleSectionLocal(sections.getById(1));
            expect(matrix.getCell("room-2", 3).section).not.toEqual(sections.getById(1));
        });

        it("fires a schedule-changed event", function(){
            var event_fired = false;
            $j("body").on("schedule-changed", function(){
                event_fired = true;
            })
            sections.unscheduleSectionLocal(sections.getById(1));
            expect(event_fired).toBeTrue();
        });

        it("modifies the schedule_assignments data structure", function(){
            expect(sections.scheduleAssignments[1]).toEqual({room_name: "room-1", timeslots: [3], id: 1});
            sections.unscheduleSectionLocal(sections.getById(1));
            expect(sections.scheduleAssignments[1]).toEqual({room_name: null, timeslots: [], id: 1});
        });
    });


    describe("scheduleAsGhost", function() {
        it("displays the section as a ghost", function() {
            var section = sections.getById(3);
            console.log(sections);
            sections.selectSection(section);
            sections.scheduleAsGhost("room-3", 11);
            expect(matrix.getCell("room-3", 11).el.hasClass("ghost-section")).toBeTrue();
            expect(matrix.getCell("room-3", 13).el.hasClass("ghost-section")).toBeTrue();
        });

    });

    describe("unscheduleAsGhost", function() {
        it("removes section from all cells", function() {
            var section = sections.getById(3);
            sections.selectSection(section);
            sections.scheduleAsGhost("room-3", 11);
            sections.unscheduleAsGhost();
        });
    });
});
