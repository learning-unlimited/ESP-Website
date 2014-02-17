describe("Cell", function(){
    beforeEach(function(){
	c = new Cell($j("<td/>"))

	section = {
	    emailcode: "my-emailcode"
	}
    })

    it("has an element with the matrix cell class", function(){
	expect(c.el).toBeDefined()
	expect(c.el.hasClass("matrix-cell")).toBeTrue()
    })

    describe("init", function(){
	describe("with a section", function(){
	    it("has a section", function(){
		spyOn(c, 'addSection')
		c.init(section)
		expect(c.addSection).toHaveBeenCalledWith(section)
	    })
	})

	describe("without a section", function(){
	    it("calls removeSection", function(){
		spyOn(c, 'removeSection')
		c.init(null)
		expect(c.removeSection).toHaveBeenCalled()
	    })
	})
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
	it("calls droppable", function(){
	    spyOn(c.el, 'droppable')
	    c.removeSection()
	    expect(c.el.droppable).toHaveBeenCalled()
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
