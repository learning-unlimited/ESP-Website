csrf_token = function(){
    return "abcd"
}

describe("ApiClient", function(){
    var a

    beforeEach(function(){
	a = new ApiClient()
    })

    describe("schedule_section", function(){
	it("makes an ajax request", function(){
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
	var request, callback;

	beforeEach(function(){
	    jasmine.Ajax.useMock()
	    callback = jasmine.createSpy('callback')
	    
	    a.send_request({}, callback)
	    request = mostRecentAjaxRequest()
	})

	describe("when there is an error", function(){
	    beforeEach(function(){
		request.response({
		    status: 500,
		    responseText: ''
		})
	    })
	    it("does not execute the callback", function(){
		expect(callback).not.toHaveBeenCalled()
	    })
	})

	describe("when the request comes back with failure", function(){
	    beforeEach(function(){
		request.response({
		    status: 200,
		    responseText: '{"ret":false}'
		})
	    })
	    it("does not execute the callback", function(){
		expect(callback).not.toHaveBeenCalled()
	    })
	})

	describe("when the request comes back with success", function(){
	    beforeEach(function(){
		request.response({
		    status: 200,
		    responseText: '{"ret":true}'
		})	
		
	    })
	    it("executes the callback", function(){
		expect(callback).toHaveBeenCalled()
	    })
	})
    })
})
