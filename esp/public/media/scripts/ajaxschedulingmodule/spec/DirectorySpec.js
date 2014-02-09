describe("ESP.Scheduling.Widgets.Directory.Entry", function(){
    var entry
    var directory

    beforeEach(function(){
	console.log("before each")
	//table_body = $j('<tbody id="directory-table-body"></tbody>')
	directory = new ESP.Scheduling.Widgets.Directory([])

	section = ESP.Scheduling.Resources.create('Section',{
            code: "my_emailcode",
	    text: "my-cool-spark-class",
	    block_contents: ESP.Utilities.genPopup("s-" + "1234", "my_emailcode", {}, function(node) {}, null, false),
	});
	entry = new ESP.Scheduling.Widgets.Directory.Entry(directory, section)
    })

    it("should have a title", function(){
	console.log(entry.section)
	expect(entry.section.text).toMatch("my-cool-spark-class")
    })

    afterEach(function(){
	$j("#ajax-dom").hide()
    })
})
