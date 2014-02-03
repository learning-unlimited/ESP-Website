describe("ESP.Scheduling.Widgets.Directory.Entry", function(){
    var entry
    var directory

    beforeEach(function(){
	directory = new ESP.Scheduling.Widgets.Directory([])
	data = {}
	entry = new ESP.Scheduling.Widgets.Directory.Entry(directory, data)
    })

    it("should have a title", function(){
	expect(entry.el).toEqual("bla")
    })
})