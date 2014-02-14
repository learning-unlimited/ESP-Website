describe("Cell", function(){
    beforeEach(function(){
	c = new Cell($j("<td/>"))

	section = {
	    emailcode: "my-emailcode"
	}
    })

    it("has an element", function(){
	expect(c.el).toBeDefined()
	expect(c.el.hasClass("matrix-cell")).toBeTrue()
    })

    it("starts with a null section", function(){
	expect(c.section).toBeNull()
    })

    describe("adding a section", function(){
	beforeEach(function(){
	    c.removeSection()
	})
	it("saves off the section", function(){
	    c.addSection(section)
	    expect(c.section).toEqual(section)
	})
	it("adds the section to the element", function(){
	    c.addSection(section)
	    expect(c.el[0].innerHTML).toEqual(section.emailcode)
	})
	it("adds styling to the el", function(){
	    c.addSection(section)
	    expect(c.el.hasClass("occupied-cell")).toBeTrue()
	    expect(c.el.hasClass("available-cell")).toBeFalse()
	})
	it("makes the el draggable", function(){
	    spyOn(c.el, 'draggable')
	    c.addSection(section)
	    expect(c.el.draggable).toHaveBeenCalled()
	})
    })

    describe("removing a section", function(){
	beforeEach(function(){
	    c.addSection(section)
	})

	//TODO:  break this into separate its
	it("removes the section", function(){
	    c.removeSection()
	    expect(c.section).toBeNull()
	})
	it("changes the el contents", function(){
	    c.removeSection()
	    expect(c.el[0].innerHTML).not.toMatch(section.emailcode)
	})

	it("changes the cell styling", function(){
	    c.removeSection()
	    expect(c.el.hasClass("occupied-cell")).toBeFalse()
	    expect(c.el.hasClass("available-cell")).toBeTrue()
	})
    })

    describe("hasSection", function(){
	it("returns true when the cell has a section", function(){
	    c.addSection({})
	    expect(c.hasSection()).toBeTrue()
	})

	it("returns false when there is no section", function(){
	    expect(c.hasSection()).toBeFalse()
	})
    })
})
