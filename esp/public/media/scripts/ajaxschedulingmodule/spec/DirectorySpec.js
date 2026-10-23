const { generateFakeMatrix } = require("./FakeMatrix");
const { schedule_assignment_fixture } = require("./TestFixtures");

describe("Directory", function(){
    var d, m;

    beforeEach(function(){
        m = generateFakeMatrix();
        d = new Directory(m.sections,
            $j("<div/>"), schedule_assignment_fixture(), m);
    });

    it("should have a list of sections and an el", function(){
        expect(d.sections).toBe(m.sections);
        expect(d.el[0]).toBeInstanceOf(HTMLElement);
    });

    describe("render", function(){
        beforeEach(function(){
            d.render();
        });

        describe("when there are classes scheduled", function(){
            it("should not show them in the directory", function(){
                expect(d.el.children().length).toEqual(1);
                var table = d.el.children()[0];
                expect(table.rows.length).toEqual(4);
                expect(table.innerHTML).not.toMatch("S11s1");
                expect(table.innerHTML).not.toMatch("A22s1");
            });
        });

        it("should present a list of classes with emailcodes", function (){
            expect(d.el.children().length).toEqual(1);
            var table = d.el.children()[0];
            expect(table.rows.length).toEqual(4);
            expect(table.rows[0].innerHTML).toMatch("Fascinating Science Phenomena");
            expect(table.rows[0].innerHTML).toMatch("S11s2");
            expect(table.rows[0].innerHTML).toMatch("manageclass/");
            expect(table.rows[0].innerHTML).toMatch("editclass/");
        });

        it("should be able to render twice without duplicating content", async function(){
            d.render();
            d.render();
            //since we delete the old nodes asynchronously
            //need to add some asynchrony here
            await new Promise(function(resolve){ setTimeout(resolve, 0); });
            expect(d.el.children().length).toEqual(1);
        });
    });
});

describe("TableRow", function(){
    var m, d, tr;

    beforeEach(function(){
        m = generateFakeMatrix();
        d = new Directory(m.sections, $j("<div/>"), schedule_assignment_fixture(), m);
        tr = new TableRow({title: "my-title", emailcode: "M1234s1", parent_class: 1234, flags: ""}, $j("<tr/>"), d);
    })

    it("should have an el", function(){
        expect(tr.el[0]).toBeInstanceOf(HTMLElement);
    });

    it("should have a section", function(){
        expect(tr.section.title).toEqual("my-title");
    });

    it("should have a cell", function(){
        expect(tr.cell).toBeInstanceOf(Cell);
        expect(tr.section.directoryCell).toBe(tr.cell);
    });

    describe("render", function(){
        it("should display the section name", function(){
            tr.render();
            expect(tr.el[0].innerHTML).toContain("my-title");
            });

        it("should display the section email code", function(){
            tr.render();
            expect(tr.el[0].innerHTML).toContain("M1234s1");
            });

        it("has edit, manage, and class availability links", function(){
            tr.render();
            expect(tr.el[0].innerHTML).toContain("/manage/TestProgram/2026_Summer/editclass/1234");
            expect(tr.el[0].innerHTML).toContain("/manage/TestProgram/2026_Summer/manageclass/1234");
            expect(tr.el[0].innerHTML).toContain("/manage/TestProgram/2026_Summer/classavailability/1234");
        });
    });
});
