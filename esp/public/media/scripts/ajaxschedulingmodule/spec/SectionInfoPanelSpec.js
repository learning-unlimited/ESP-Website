describe("SectionInfoPanel", function() {
    var sipToggle;
    var sipNoToggle;
    var sections;
    beforeEach(function() {
        sections = new Sections(section_fixture(), {}, teacher_fixture(),
                                    schedule_assignment_fixture(), new FakeApiClient());
        sipNoToggle = new SectionInfoPanel($j("<div>"), sections, null);
        sipToggle = new SectionInfoPanel($j("<div>"), sections, new MessagePanel($j("<div>"), "Initial Message"));
    });

    describe("hide", function() {
        it("should add a ui-helper-hidden class", function() {
            sipNoToggle.hide();
            expect(sipNoToggle.el.hasClass("ui-helper-hidden")).toBeTrue();
        });

        it("should remove the ui-helper-hidden class from togglePanel if present", function() {
            sipToggle.hide();
            expect(sipToggle.togglePanel.el.hasClass("ui-helper-hidden")).toBeFalse();

        });
    });

    describe("show", function() {
        it("should remove a ui-helper-hidden class", function() {
            sipNoToggle.show();
            expect(sipNoToggle.el.hasClass("ui-helper-hidden")).toBeFalse();
        });

        it("should add the ui-helper-hidden class from togglePanel if present", function() {
            sipToggle.show();
            expect(sipToggle.togglePanel.el.hasClass("ui-helper-hidden")).toBeTrue();

        });
    });

    describe("displaySection", function() {
        it("should have the important information in it", function() {
            sipNoToggle.displaySection(sections.getById(1));
            expect(sipNoToggle.el[0].innerHTML).toContain("S11s1");
            expect(sipNoToggle.el[0].innerHTML).toContain("Fascinating Science Phenomena");
            expect(sipNoToggle.el[0].innerHTML).toContain("Alyssa P. Hacker");
            expect(sipNoToggle.el[0].innerHTML).toContain("Ben Bitdiddle");
            expect(sipNoToggle.el[0].innerHTML).toContain("150");
            expect(sipNoToggle.el[0].innerHTML).toContain("Length: </b>1");
            expect(sipNoToggle.el[0].innerHTML).toContain("9-12");

        });
    });

});
