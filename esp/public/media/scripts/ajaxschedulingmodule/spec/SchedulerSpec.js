describe("Scheduler", function(){
    beforeEach(function(){
	s = new Scheduler({}, $j("<div/>")[0], $j("<div/>")[0])
    })

    it("should have a directory and a matrix", function(){
	//TODO:  can we assert on the types of these?
	expect(s.directory).toBeDefined()
	expect(s.matrix).toBeDefined()
    })

    describe("render", function(){
	it("calls render on the directory and matrix",  function(){
	    spyOn(s.directory, "render")
	    spyOn(s.matrix, "render")
	    s.render()
	    expect(s.directory.render).toHaveBeenCalled()
	    expect(s.matrix.render).toHaveBeenCalled()
	})
    })
})

var data = {sections: {
	3329: {
	    status: 10, 
	    category: 'S', 
	    parent_class: 3188, 
	    emailcode: 'S3188s1', 
	    index: 1, 
	    title: "Fascinating Science Phenomena", 
	    category_id: 17, 
	    class_size_max: 150, 
	    length: 1.83, 
	    grade_min: 7, 
	    num_students: 42, 
	    grade_max: 12, 
	    id: 3329, 
	    teachers: [6460]
	}, 
	3538: {
	    status: 10, 
	    category: 'M', 
	    parent_class: 3343, 
	    emailcode: 'M3343s1', 
	    index: 1, 
	    title: "Become a LaTeX Guru", 
	    category_id: 16, 
	    class_size_max: 15, 
	    length: 1.83, 
	    grade_min: 7, 
	    num_students: 14, 
	    grade_max: 12, 
	    id: 3538, 
	    teachers: [45225]
	}
}}

describe("Matrix", function(){
    beforeEach(function(){
	m = new Matrix($j("<div/>")[0])
    })

    it("should have an element", function(){
	expect(m.el).toBeHtmlNode()
    })
})

describe("Directory", function(){
    beforeEach(function(){
	d = new Directory(data.sections, $j("<div/>")[0])
    })

    it("should have a list of sections and an el", function(){
	expect(d.sections).toBeObject()
	expect(d.el).toBeHtmlNode()
    })

    describe("render", function(){
	beforeEach(function(){
	    d.render()
	})

	it("el", function (){
	    expect(d.el.children.length).toEqual(1)
	    table = d.el.children[0]
	    expect(table.rows.length).toEqual(2)
	    expect(table.rows[0].innerHTML).toMatch("Fascinating Science Phenomena")
	    expect(table.rows[1].innerHTML).toMatch("Become a LaTeX Guru")
	})
    })
})
