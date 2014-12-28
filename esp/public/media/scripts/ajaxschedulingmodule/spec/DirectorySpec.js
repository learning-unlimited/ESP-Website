describe("Directory", function(){
    var d;

    beforeEach(function(){
        m = matrix_fixture();
	    d = new Directory(sections_fixture(), $j("<div/>"), empty_schedule_assignments_fixture(), m);
    });

    it("should have a list of sections and an el", function(){
	expect(d.sections).toBeObject();
	expect(d.el[0]).toBeHtmlNode();
    });

    describe("render", function(){
	beforeEach(function(){
	    d.render();
	});

	describe("when there are classes scheduled", function(){
	    beforeEach(function(){
            m = matrix_fixture();
		    d = new Directory(sections_fixture(), $j("<div/>"), schedule_assignments_fixture(), m);
		    d.render();
	    });

	    it("should not show them in the directory", function(){
		expect(d.el.children().length).toEqual(1);
		var table = d.el.children()[0];
		expect(table.rows.length).toEqual(1);
		expect(table.rows[0].innerHTML).toMatch("Become a LaTeX Guru");
		expect(table.rows[0].innerHTML).toMatch("M3343s1");
	    });
	});

	it("should present a list of classes with emailcodes", function (){
	    expect(d.el.children().length).toEqual(1);
	    var table = d.el.children()[0];
	    expect(table.rows.length).toEqual(2);
	    expect(table.rows[0].innerHTML).toMatch("Fascinating Science Phenomena");
	    expect(table.rows[0].innerHTML).toMatch("S3188s1");
	    expect(table.rows[1].innerHTML).toMatch("Become a LaTeX Guru");
	    expect(table.rows[1].innerHTML).toMatch("M3343s1");
	});

	it("should be able to render twice without duplicating content", function(){
	    runs(function(){
		d.render();
		d.render();
	    });
	    //since we delete the old nodes asynchronously
	    //need to add some asynchrony here
	    waits(0);
	    runs(function(){
		expect(d.el.children().length).toEqual(1);
	    });
	});
    });
});

describe("TableRow", function(){
    var tr;

    beforeEach(function(){
        m = matrix_fixture();
		d = new Directory(sections_fixture(), $j("<div/>"), schedule_assignments_fixture(), m);
	    tr = new TableRow({title: "my-title", emailcode: "my-emailcode", parent_class: 1234}, $j("<tr/>"), d);
    })

    it("should have an el", function(){
	expect(tr.el[0]).toBeHtmlNode();
    });

    it("should have a section", function(){
	expect(tr.section).toBeObject();
    });

    it("should have a cell", function(){
	expect(tr.cell).toBeObject();
    });

    describe("render", function(){
	it("should display the section name", function(){
	    tr.render();
	    expect(tr.el[0].innerHTML).toContain("my-title");
	});

	it("shsould display the section email code", function(){
	    tr.render();
	    expect(tr.el[0].innerHTML).toContain("my-emailcode");
	});

	it("includes the draggable cell", function(){
	    tr.render();
	    expect(tr.el[0].innerHTML).toContain(tr.cell.el[0].outerHTML);
	});
    });

    describe("hide", function(){
	it("sets the display style to 'none'", function(){
	    tr.hide();
	    expect(tr.el[0].style.display).toEqual("none");
	});
    });

    describe("unHide", function(){
	it("unsets the display style from 'none'", function(){
	    tr.hide();
	    tr.unHide();
	    expect(tr.el[0].style.display).not.toEqual("none");
	});
    });
});
