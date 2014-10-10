describe("CellColors", function(){
    var cc;

    beforeEach(function(){
	cc = new CellColors()
	section = { 
	    emailcode: "S1234s1",
	}
	section2 = {
	    emailcode: "S1235s1",
	}
    })

    describe("color", function(){
	it("should return a valid color code", function(){
	    var color = cc.color(section)
	    expect(color).toBeString()
	    expect(color).toBeSameLengthAs("#123456")
	    expect(color).toStartWith("#")
	    valid_characters = ["0", "1","2","3","4","5","6","7","8","9","A","B","C","D","E","F"]
	    characters = color.substr(1)
	    for (i in characters){
		var c = characters[i]
		expect(valid_characters.indexOf(c)).toBeGreaterThan(-1)
	    }	    
	})

	it("should return different colors for different classes", function(){
	    var color1 = cc.color(section)
	    var color2 = cc.color(section2)
	    expect(color1).not.toEqual(color2)
	})
    })
})
