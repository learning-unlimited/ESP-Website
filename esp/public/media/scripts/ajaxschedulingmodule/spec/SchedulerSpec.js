describe("Scheduler", function(){
    beforeEach(function(){
	//TODO:  what data should be passed in?
	s = new Scheduler([])
    })

    it("should have a directory", function(){
	expect(s.directory).toBeDefined()
    })

    it("should have a matrix", function(){
	expect(s.matrix).toBeDefined()
    })

})
