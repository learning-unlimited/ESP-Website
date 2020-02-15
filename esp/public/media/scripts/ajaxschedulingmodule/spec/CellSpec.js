describe("Cell", function(){
    var c, section, section2;

    beforeEach(function(){
        var matrix = generateFakeMatrix();
        c = new Cell($j("<td/>"), null, "1-115", 1, matrix);
        section = matrix.sections.getById(1);
        section.emailcode = 'S1111s1';
        section2 = matrix.sections.getById(3);
        section2.emailcode = 'A2222s1';
    });

    // Initialization Tests

    it("has an element with the matrix cell class", function(){
        expect(c.el).toBeDefined();
        expect(c.el.hasClass("matrix-cell")).toBeTrue();
    });

    it("has a room attached as data on the el", function(){
        expect(c.room_name).toEqual("1-115");
    });

    it("has a timeslot", function(){
        expect(c.timeslot_id).toEqual(1);
    });

    it("attaches itself to its el", function(){
        expect($j(c.el).data("cell")).toEqual(c);
    });

    describe("with a section", function(){
        it("has a section", function(){
            spyOn(c, 'addSection');
            c.init(section);
            expect(c.addSection).toHaveBeenCalledWith(section);
        });
    });

    describe("without a section", function(){
        it("calls removeSection", function(){
            spyOn(c, 'removeSection');
            c.init(null);
            expect(c.removeSection).toHaveBeenCalled();
        });
    });


    describe("select", function() {
        it("adds the class selected-section", function() {
            c.addSection(section);
            c.select();
            expect(c.el.hasClass("selected-section")).toBeTrue();

        });
    });

    describe("unselect", function() {
        it("removes the class selected-section", function() {
            c.addSection(section);
            c.select();
            c.unselect();
            expect(c.el.hasClass("selected-section")).toBeFalse();
        });

        it("does nothing if class was not already selected", function() {
            c.addSection(section);
            c.unselect();
            expect(c.el.hasClass("selected-section")).toBeFalse();
        });

    });

    describe("tooltip", function(){
        beforeEach(function(){
            var s = c.matrix.sections.getById(1);
            c.addSection(s);
            });

        it("contains the emailcode, title, length, and max students", function(){
            var tooltip = c.tooltip();
            expect(tooltip).toContain("S1111s1");
            expect(tooltip).toContain("Ben Bitdiddle");
            expect(tooltip).toContain("Alyssa P. Hacker");
            expect(tooltip).toContain("Fascinating Science Phenomena");
            expect(tooltip).toContain("Class size max</b>: 150");
            expect(tooltip).toContain("Length</b>: 1");
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
            expect(c.el.hasClass("occupied-cell")).toBeTrue();
            expect(c.el.hasClass("available-cell")).toBeFalse();
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
            expect(c.el.hasClass("occupied-cell")).toBeFalse();
            expect(c.el.hasClass("available-cell")).toBeTrue();
        });
    });

    describe("addGhostSection", function() {
        it("adds the correct styling to the cell", function() {
            c.addSection(section);
            c.addGhostSection(section2);
            expect(c.el[0].innerHTML).toMatch(section2.emailcode);
            expect(c.el[0].innerHTML).not.toMatch(section.emailcode);
            expect($j(c.el[0]).css('background-color')).toEqual('rgb(32, 32, 32)');
            expect(c.el.hasClass("ghost-section")).toBeTrue();
        });

    });

    describe("removeGhostSection", function() {
        var originalBackgroundColor;
        beforeEach(function() {
            originalBackgroundColor = $j(c.el[0]).css('background-color');
            c.addSection(section);
            c.addGhostSection(section2);
        });
        it("removes the styling from the cell", function() {
            c.removeGhostSection();
            expect(c.el[0].innerHTML).not.toMatch(section2.emailcode);
            expect(c.el.hasClass("ghost-section")).toBeFalse();
        });

        it("puts back the section previously scheduled if it exists", function() {
            c.removeGhostSection();
            expect(c.el[0].innerHTML).toMatch(section.emailcode);
            expect(c.el[0].innerHTML).toMatch("</a>");
            expect($j(c.el[0]).css('background-color')).toEqual('rgb(16, 16, 16)');
            expect($j(c.el[0]).css('color')).toEqual('rgb(255, 255, 255)');
        });

        it("returns the cell to its previous styling otherwise", function() {
            c.removeSection(section);
            c.removeGhostSection();
            expect(c.el[0].innerHTML).toEqual("");
            expect($j(c.el[0]).css('background-color')).toEqual(originalBackgroundColor);
        });
    });


});
