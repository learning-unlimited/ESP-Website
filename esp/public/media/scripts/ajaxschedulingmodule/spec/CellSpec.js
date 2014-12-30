describe("Cell", function(){
    var c;
    var section;

    beforeEach(function(){
        var mp = new MessagePanel($j("<div>"), "Welcome to the Ajax Scheduler!");
        var sip = new SectionInfoPanel($j("<div>"), teacher_fixture(), mp);
        matrix = matrix_fixture();
	    c = new Cell($j("<td/>"), null, "1-115", 1, matrix);
	    section = {
	        emailcode: "my-emailcode",
	        length: 1.83,
	    };
    });

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


    describe("tooltip", function(){
	    beforeEach(function(){
            var s = section_2();
            s.teacher_data = [teacher_fixture()[2]]
	        c.addSection(s);
	    });

	    it("contains the emailcode, title, length, and max students", function(){
	        var tooltip = c.tooltip();
	        expect(tooltip).toContain("M3343s1");
            expect(tooltip).toContain("Ben Bitdiddle");
	        expect(tooltip).toContain("Become a LaTeX Guru");
	        expect(tooltip).toContain("Class size max: 15");
	        expect(tooltip).toContain("Length: 2");
	    });
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
	        expect(c.el[0].innerText).toEqual(section.emailcode);
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

    describe("select", function() {
        it("adds the class selected-section", function() {
            var s = section_1();
            s.teacher_data = [];
	        c.addSection(s);
            c.select();
	        expect(c.el.hasClass("selected-section")).toBeTrue();

        });
    });

    describe("unselect", function() {
        it("removes the class selected-section", function() {
            var s = section_2();
            s.teacher_data = [];
	        c.addSection(s);
            c.select();
            c.unselect();
	        expect(c.el.hasClass("selected-section")).toBeFalse();
        });

        it("does nothing if class was not already selected", function() {
	        c.addSection(section_2());
            c.unselect();
	        expect(c.el.hasClass("selected-section")).toBeFalse();
        });
        
    });

});
