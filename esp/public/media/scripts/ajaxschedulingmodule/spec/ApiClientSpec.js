csrf_token = function(){
    return "abcd"
}

describe("ApiClient", function(){
    describe("schedule_section", function(){
	it("makes an ajax request", function(){
	    var a = new ApiClient()
	    spyOn(a, "send_request")
	    var callback_function = function(){}
	    
	    a.schedule_section(1234, 1, "my-room", callback_function)

	    expect(a.send_request).toHaveBeenCalledWith(
		{
		    action: 'assignreg',
		    csrfmiddlewaretoken: 'abcd',
		    cls: 1234,
		    block_room_assignments: '1,my-room',
		}, 
		callback_function
	    )	    
	})
    })

    describe("unschedule_section", function(){
	it("makes an ajax request", function(){
	    var a = new ApiClient()
	    spyOn(a, "send_request")
	    var callback_function = function(){}
	    
	    a.unschedule_section(1234, callback_function)

	    expect(a.send_request).toHaveBeenCalledWith(
		{
		    action: 'deletereg',
		    csrfmiddlewaretoken: 'abcd',
		    cls: 1234,
		}, 
		callback_function
	    )
	})
    })

    describe("send_request", function(){
	describe("when there is an error", function(){
	    it("does not execute the callback", function(){
		
	    })
	})

	describe("when the request comes back with failure", function(){
	    it("does not execute the callback", function(){
	    })
	})

	describe("when the request comes back with success", function(){
	    it("executes the callback", function(){
	    })
	})
    })
})
