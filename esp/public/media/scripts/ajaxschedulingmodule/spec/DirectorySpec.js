describe("ESP.Scheduling.Widgets.Directory.Entry", function(){
    var entry
    var directory

    beforeEach(function(){
	directory = new ESP.Scheduling.Widgets.Directory([])

	section = ESP.Scheduling.Resources.create('Section',{
            code: "my_emailcode",
	    //TODO:  should be "title", not "text"
	    text: "my-cool-spark-class",
	    //TODO:  get rid of block_contents
	    block_contents: ESP.Utilities.genPopup("s-" + "1234", "my_emailcode", {}, function(node) {}, null, false),
	});
	entry = new ESP.Scheduling.Widgets.Directory.Entry(directory, section)
    })

    it("should have a title", function(){
	console.log(entry.el[0])
	expect(entry.el[0].innerHTML).toMatch("my-cool-spark-class")
    })

    afterEach(function(){
	$j("#ajax-dom").hide()
    })
})

describe("ESP.Scheduling.Widgets.Directory", function(){
    beforeEach(function() {
	section = ESP.Scheduling.Resources.create('Section',{
            code: "my_emailcode",
	    //TODO:  should be "title", not "text"
	    text: "my-cool-spark-class",
	    //TODO:  get rid of block_contents
	    block_contents: ESP.Utilities.genPopup("s-" + "1234", "my_emailcode", {}, function(node) {}, null, false),
	})

	directory = new ESP.Scheduling.Widgets.Directory([section])
    })

    it("should have some entries", function(){
	expect(directory.entries.length).toEqual(1)
    })
})
