describe("Scheduler", function(){
    beforeEach(function(){
	s = new Scheduler({schedule_assignments: {}, rooms: {}, timeslots: {}, sections: {}}, $j("<div/>"), $j("<div/>"), $j("<div/>"))
    })

    it("should have a directory and a matrix", function(){
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
