const { FakeApiClient } = require("./FakeApiClient");
const {
    category_fixture,
    schedule_assignment_fixture,
    section_fixture,
    teacher_fixture,
} = require("./TestFixtures");

describe("SectionInfoPanel", function() {
    var sipToggle;
    var sipNoToggle;
    var sections;
    beforeEach(function() {
        sections = new Sections(section_fixture(), {}, category_fixture(), teacher_fixture(), {},
                                    schedule_assignment_fixture(), new FakeApiClient());
        sipNoToggle = new SectionInfoPanel($j("<div>"), sections, null);
        sipToggle = new SectionInfoPanel($j("<div>"), sections, new MessagePanel($j("<div>"), "<i>Initial Message</i>"));
    });

    it("should keep the initial message in the toggle panel", function() {
        expect(sipToggle.togglePanel.el[0].innerHTML).toEqual("<i>Initial Message</i>");
    });

    describe("hide", function() {
        it("should add a ui-helper-hidden class", function() {
            sipNoToggle.hide();
            expect(sipNoToggle.el.hasClass("ui-helper-hidden")).toBe(true);
        });

        it("should remove the ui-helper-hidden class from togglePanel if present", function() {
            sipToggle.hide();
            expect(sipToggle.togglePanel.el.hasClass("ui-helper-hidden")).toBe(false);

        });
    });

    describe("show", function() {
        it("should remove a ui-helper-hidden class", function() {
            sipNoToggle.show();
            expect(sipNoToggle.el.hasClass("ui-helper-hidden")).toBe(false);
        });

        it("should add the ui-helper-hidden class from togglePanel if present", function() {
            sipToggle.show();
            expect(sipToggle.togglePanel.el.hasClass("ui-helper-hidden")).toBe(true);

        });
    });

    describe("displaySection", function() {
        it("should have the important information in it", function() {
            sipNoToggle.displaySection(sections.getById(1));
            expect(sipNoToggle.el[0].innerHTML).toContain("S11s1");
            expect(sipNoToggle.el[0].innerHTML).toContain("Fascinating Science Phenomena");
            expect(sipNoToggle.el[0].innerHTML).toContain("Science");
            expect(sipNoToggle.el[0].innerHTML).toContain("Alyssa P. Hacker");
            expect(sipNoToggle.el[0].innerHTML).toContain("Ben Bitdiddle");
            expect(sipNoToggle.el[0].innerHTML).toContain("150");
            expect(sipNoToggle.el[0].innerHTML).toContain("Length: </b> 50 minutes");
            expect(sipNoToggle.el[0].innerHTML).toContain("9-12");

        });

        it("offers to unschedule only scheduled sections", function() {
            sipNoToggle.displaySection(sections.getById(1));
            expect(sipNoToggle.el[0].innerHTML).toContain("Unschedule Section");

            sipNoToggle.displaySection(sections.getById(2));
            expect(sipNoToggle.el[0].innerHTML).not.toContain("Unschedule Section");
        });
    });

});
