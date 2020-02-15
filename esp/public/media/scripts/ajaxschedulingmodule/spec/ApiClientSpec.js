csrf_token = function(){
    return "abcd";
};

describe("ApiClient", function(){
    var a;
    beforeEach(function(){
        a = new ApiClient();
    });

    describe("get_change_log", function(){
        var request, callback, errorReporter;

        beforeEach(function(){
            jasmine.Ajax.useMock();
            callback = jasmine.createSpy('callback');
            errorReporter = jasmine.createSpy('errorReporter');

            a.get_change_log(0, callback, errorReporter);
            request = mostRecentAjaxRequest();
        });

        describe("when there is an error", function(){
            beforeEach(function(){
                request.response({
                    status: 500,
                    responseText: 'an error has occurred'
                });
            });

            it("does not execute the callback", function(){
                expect(callback).not.toHaveBeenCalled();
                expect(errorReporter).toHaveBeenCalledWith("An error occurred fetching the changelog.");
            });
        });

        describe("when the request comes back with success", function(){
            beforeEach(function(){
                request.response({
                    status: 200,
                    responseText: '{"changelog":[], "other":[]}'
                });
            });

            it("executes the callback", function(){
                expect(callback).toHaveBeenCalled();
                expect(errorReporter).not.toHaveBeenCalled();
            });
        });
    });

    describe("schedule_section", function(){
        it("makes an ajax request", function(){
            spyOn(a, "send_request");
            var callback_function = function(){};
            var errorReporter_function = function(){};

            a.schedule_section(1234, [1], "my-room",
                               callback_function,
                               errorReporter_function);

            expect(a.send_request).toHaveBeenCalledWith(
                {
                    action: 'assignreg',
                    csrfmiddlewaretoken: 'abcd',
                    cls: 1234,
                    block_room_assignments: '1,my-room',
                },
                callback_function,
                errorReporter_function
            );
        });

        it("can send a request with multiple timeslots", function(){
            spyOn(a, "send_request");
            var callback_function = function(){};
            var errorReporter_function = function(){};

            a.schedule_section(1234, [1,2], "my-room",
                               callback_function,
                               errorReporter_function);

            expect(a.send_request).toHaveBeenCalledWith(
                {
                    action: 'assignreg',
                    csrfmiddlewaretoken: 'abcd',
                    cls: 1234,
                    block_room_assignments: '1,my-room\n2,my-room',
                },
                callback_function,
                errorReporter_function
            );
        });
    });

    describe("unschedule_section", function(){
        it("makes an ajax request", function(){
            spyOn(a, "send_request");
            var callback_function = function(){};
            var errorReporter_function = function(){};

            a.unschedule_section(1234, callback_function, errorReporter_function);

            expect(a.send_request).toHaveBeenCalledWith(
                {
                    action: 'deletereg',
                    csrfmiddlewaretoken: 'abcd',
                    cls: 1234,
                },
                callback_function,
                errorReporter_function
            );
        });
    });

    describe("send_request", function(){
        var request, callback, errorReporter;

        beforeEach(function(){
            jasmine.Ajax.useMock();
            callback = jasmine.createSpy('callback');
            errorReporter = jasmine.createSpy('errorReporter');

            a.send_request({}, callback, errorReporter);
            request = mostRecentAjaxRequest();
        });

        describe("when there is an error", function(){
            beforeEach(function(){
                request.response({
                    status: 500,
                    responseText: 'an error has occurred'
                });
            });
            it("does not execute the callback", function(){
                expect(callback).not.toHaveBeenCalled();
                expect(errorReporter).toHaveBeenCalledWith("An error occurred saving the schedule change.");
            });
        });

        describe("when the request comes back with failure", function(){
            beforeEach(function(){
                request.response({
                    status: 200,
                    responseText: '{"ret":false,"msg":"The teacher is not available"}'
                });
            });
            it("does not execute the callback", function(){
                expect(callback).not.toHaveBeenCalled();
                expect(errorReporter).toHaveBeenCalledWith("The teacher is not available");
            });
        });

        describe("when the request comes back with success", function(){
            beforeEach(function(){
                request.response({
                    status: 200,
                    responseText: '{"ret":true}'
                });

            });
            it("executes the callback", function(){
                expect(callback).toHaveBeenCalled();
                expect(errorReporter).not.toHaveBeenCalled();
            });
        });
    });

});
