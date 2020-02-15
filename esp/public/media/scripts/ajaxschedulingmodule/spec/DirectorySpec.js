describe("Directory", function(){
    var d, m;

    beforeEach(function(){
        m = generateFakeMatrix();
        d = new Directory(m.sections,
            $j("<div/>"), schedule_assignment_fixture(), m);
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
                d = new Directory(m.sections, $j("<div/>"), schedule_assignment_fixture(), m);
                d.render();
                })

            it("should not show them in the directory", function(){
                expect(d.el.children().length).toEqual(1);
                var table = d.el.children()[0];
                expect(table.rows.length).toEqual(4);
                expect(table.rows[0].innerHTML).toMatch("Fascinating Science Phenomena");
                expect(table.rows[0].innerHTML).toMatch("manageclass/");
                expect(table.rows[0].innerHTML).toMatch("editclass/");
            });
        });

        it("should present a list of classes with emailcodes", function (){
            expect(d.el.children().length).toEqual(1);
            var table = d.el.children()[0];
            expect(table.rows.length).toEqual(4);
            expect(table.rows[0].innerHTML).toMatch("Fascinating Science Phenomena");
            expect(table.rows[0].innerHTML).toMatch("S11s2");
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
    var m, d, tr;

    beforeEach(function(){
        m = generateFakeMatrix();
        d = new Directory(m.sections, $j("<div/>"), schedule_assignment_fixture(), m);
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

        it("should display the section email code", function(){
            tr.render();
            expect(tr.el[0].innerHTML).toContain("my-emailcode");
            });

        it("has edit and manage links", function(){
            tr.render();
            expect(tr.el[0].innerHTML).toContain("editclass/");
            expect(tr.el[0].innerHTML).toContain("manageclass/");
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
