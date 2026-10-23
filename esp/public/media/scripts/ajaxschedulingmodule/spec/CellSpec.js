const { generateFakeMatrix } = require("./FakeMatrix");

// Normalize a CSS color the same way setting it with jQuery does
function cssColor(value){
    return $j("<div>").css("color", value)[0].style.color;
}

describe("Cell", function(){
    var c, section, section2;

    beforeEach(function(){
        var matrix = generateFakeMatrix();
        c = new Cell($j("<td/>"), null, 101, 1, matrix);
        section = matrix.sections.getById(1);
        section.emailcode = 'S1111s1';
        section2 = matrix.sections.getById(3);
        section2.emailcode = 'A2222s1';
    });

    // Initialization Tests

    it("has an element with the matrix cell class", function(){
        expect(c.el).toBeDefined();
        expect(c.el.hasClass("matrix-cell")).toBe(true);
    });

    it("has a room", function(){
        expect(c.room_id).toEqual(101);
    });

    it("has a timeslot", function(){
        expect(c.timeslot_id).toEqual(1);
    });

    it("attaches itself to its el", function(){
        expect($j(c.el).data("cell")).toBe(c);
    });

    describe("with a section", function(){
        it("has a section", function(){
            jest.spyOn(c, 'addSection').mockImplementation(function(){});
            c.init(section);
            expect(c.addSection).toHaveBeenCalledWith(section);
        });
    });

    describe("without a section", function(){
        it("calls removeSection", function(){
            jest.spyOn(c, 'removeSection').mockImplementation(function(){});
            c.init(null);
            expect(c.removeSection).toHaveBeenCalled();
        });
    });


    describe("select", function() {
        it("adds the class selected-section", function() {
            c.addSection(section);
            c.select();
            expect(c.el.hasClass("selected-section")).toBe(true);

        });
    });

    describe("unselect", function() {
        it("removes the class selected-section", function() {
            c.addSection(section);
            c.select();
            c.unselect();
            expect(c.el.hasClass("selected-section")).toBe(false);
        });

        it("does nothing if class was not already selected", function() {
            c.addSection(section);
            c.unselect();
            expect(c.el.hasClass("selected-section")).toBe(false);
        });

    });

    describe("tooltip", function(){
        beforeEach(function(){
            var s = c.matrix.sections.getById(1);
            c.addSection(s);
            });

        it("contains the emailcode, title, category, teachers, length, and max students", function(){
            var tooltip = c.tooltip();
            expect(tooltip).toContain("S1111s1");
            expect(tooltip).toContain("Ben Bitdiddle");
            expect(tooltip).toContain("Alyssa P. Hacker");
            expect(tooltip).toContain("Fascinating Science Phenomena");
            expect(tooltip).toContain("Category</b>: Science");
            expect(tooltip).toContain("Class size max</b>: 150");
            expect(tooltip).toContain("Length</b>:  50 minutes");
        });
    });


    describe("adding a section", function(){
        beforeEach(function(){
            c.removeSection();
        });

        it("saves off the section", function(){
            c.addSection(section);
            expect(c.section).toEqual(section);
        });

        it("adds the section to the element", function(){
            c.addSection(section);
            expect(c.el[0].innerHTML).toContain(section.emailcode);
        });

        it("adds styling to the el", function(){
            c.addSection(section);
            expect(c.el.hasClass("occupied-cell")).toBe(true);
            expect(c.el.hasClass("available-cell")).toBe(false);
        });

        it("adds the section to the el data", function(){
            c.addSection(section);
            expect(c.el.data("section")).toEqual(section);
        });

    });

    describe("removing a section", function(){
        beforeEach(function(){
            c.addSection(section);
        });

        it("removes the section", function(){
            c.removeSection();
            expect(c.section).toBeNull();
        });

        it("changes the el contents", function(){
            c.removeSection();
            expect(c.el[0].innerHTML).not.toMatch(section.emailcode);
        });

        it("removes the section from the el data", function(){
            c.removeSection();
            expect(c.el.data("section")).not.toBeDefined();
        });

        it("changes the cell styling", function(){
            c.removeSection();
            expect(c.el.hasClass("occupied-cell")).toBe(false);
            expect(c.el.hasClass("available-cell")).toBe(true);
        });
    });

    describe("addGhostSection", function() {
        it("adds the correct styling to the cell", function() {
            c.addSection(section);
            c.addGhostSection(section2);
            expect(c.el[0].innerHTML).toMatch(section2.emailcode);
            expect(c.el[0].innerHTML).not.toMatch(section.emailcode);
            expect(c.el[0].style.backgroundColor).toEqual(
                cssColor(c.cellColors.RGBToString(c.cellColors.color(section2))));
            expect(c.el.hasClass("ghost-section")).toBe(true);
        });

    });

    describe("removeGhostSection", function() {
        beforeEach(function() {
            c.addSection(section);
            c.addGhostSection(section2);
        });
        it("removes the styling from the cell", function() {
            c.removeGhostSection();
            expect(c.el[0].innerHTML).not.toMatch(section2.emailcode);
            expect(c.el.hasClass("ghost-section")).toBe(false);
        });

        it("puts back the section previously scheduled if it exists", function() {
            c.removeGhostSection();
            var color = c.cellColors.color(section);
            expect(c.el[0].innerHTML).toMatch(section.emailcode);
            expect(c.el[0].innerHTML).toMatch("</a>");
            expect(c.el[0].style.backgroundColor).toEqual(cssColor(c.cellColors.RGBToString(color)));
            expect(c.el[0].style.color).toEqual(cssColor(c.cellColors.textColor(color)));
        });

        it("returns the cell to its previous styling otherwise", function() {
            c.removeSection();
            c.removeGhostSection();
            expect(c.el[0].innerHTML).toEqual("");
            expect(c.el[0].style.backgroundColor).toEqual("");
        });
    });


});
