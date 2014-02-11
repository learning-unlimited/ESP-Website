describe("Directory", function(){
    beforeEach(function(){
	d = new Directory(sections_fixture, $j("<div/>")[0])
    })

    it("should have a list of sections and an el", function(){
	expect(d.sections).toBeObject()
	expect(d.el).toBeHtmlNode()
    })

    describe("render", function(){
	beforeEach(function(){
	    d.render()
	})

	it("should present a list of classes with emailcodes", function (){
	    expect(d.el.children.length).toEqual(1)
	    table = d.el.children[0]
	    expect(table.rows.length).toEqual(2)
	    expect(table.rows[0].innerHTML).toMatch("Fascinating Science Phenomena")
	    expect(table.rows[0].innerHTML).toMatch("S3188s1")
	    expect(table.rows[1].innerHTML).toMatch("Become a LaTeX Guru")
	    expect(table.rows[1].innerHTML).toMatch("M3343s1")
	})
    })
})
