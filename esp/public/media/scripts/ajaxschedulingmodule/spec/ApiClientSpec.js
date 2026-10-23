// Fake a jQuery ajax response
function resolved(data){
    return $j.Deferred().resolve(data, "success").promise();
}

function rejected(){
    return $j.Deferred().reject({status: 500}, "error").promise();
}

describe("ApiClient", function(){
    var a;
    beforeEach(function(){
        a = new ApiClient();
    });

    describe("get_change_log", function(){
        var callback, errorReporter;

        beforeEach(function(){
            callback = jest.fn();
            errorReporter = jest.fn();
        });

        it("requests the changes after the given index", function(){
            jest.spyOn($j, "getJSON").mockReturnValue(resolved({}));
            a.get_change_log(0, callback, errorReporter);
            expect($j.getJSON).toHaveBeenCalledWith('ajax_change_log', {last_fetched_index: 0});
        });

        describe("when there is an error", function(){
            beforeEach(function(){
                jest.spyOn($j, "getJSON").mockReturnValue(rejected());
                a.get_change_log(0, callback, errorReporter);
            });

            it("does not execute the callback", function(){
                expect(callback).not.toHaveBeenCalled();
                expect(errorReporter).toHaveBeenCalledWith("An error occurred fetching the changelog.");
            });
        });

        describe("when the request comes back with success", function(){
            beforeEach(function(){
                jest.spyOn($j, "getJSON").mockReturnValue(resolved({changelog: [], other: []}));
                a.get_change_log(0, callback, errorReporter);
            });

            it("executes the callback", function(){
                expect(callback).toHaveBeenCalledWith({changelog: [], other: []});
                expect(errorReporter).not.toHaveBeenCalled();
            });
        });
    });

    describe("schedule_section", function(){
        it("makes an ajax request", function(){
            jest.spyOn(a, "send_request").mockImplementation(function(){});
            var callback_function = function(){};
            var errorReporter_function = function(){};

            a.schedule_section(1234, [1], 101, false,
                               callback_function,
                               errorReporter_function);

            expect(a.send_request).toHaveBeenCalledWith(
                'ajax_schedule_class',
                {
                    action: 'assignreg',
                    csrfmiddlewaretoken: 'abcd',
                    cls: 1234,
                    block_room_assignments: '1,101',
                    override: false,
                },
                callback_function,
                errorReporter_function
            );
        });

        it("can send a request with multiple timeslots", function(){
            jest.spyOn(a, "send_request").mockImplementation(function(){});
            var callback_function = function(){};
            var errorReporter_function = function(){};

            a.schedule_section(1234, [1,2], 101, false,
                               callback_function,
                               errorReporter_function);

            expect(a.send_request).toHaveBeenCalledWith(
                'ajax_schedule_class',
                {
                    action: 'assignreg',
                    csrfmiddlewaretoken: 'abcd',
                    cls: 1234,
                    block_room_assignments: '1,101\n2,101',
                    override: false,
                },
                callback_function,
                errorReporter_function
            );
        });
    });

    describe("unschedule_section", function(){
        it("makes an ajax request", function(){
            jest.spyOn(a, "send_request").mockImplementation(function(){});
            var callback_function = function(){};
            var errorReporter_function = function(){};

            a.unschedule_section(1234, callback_function, errorReporter_function);

            expect(a.send_request).toHaveBeenCalledWith(
                'ajax_schedule_class',
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
        var callback, errorReporter;

        beforeEach(function(){
            callback = jest.fn();
            errorReporter = jest.fn();
            // send_request logs the outcome of every request
            jest.spyOn(console, "log").mockImplementation(function(){});
        });

        it("posts the request to the given view", function(){
            jest.spyOn($j, "post").mockReturnValue(resolved({ret: true}));
            a.send_request('ajax_schedule_class', {cls: 1234}, callback, errorReporter);
            expect($j.post).toHaveBeenCalledWith('ajax_schedule_class', {cls: 1234}, "json");
        });

        describe("when there is an error", function(){
            beforeEach(function(){
                jest.spyOn($j, "post").mockReturnValue(rejected());
                a.send_request('ajax_schedule_class', {}, callback, errorReporter);
            });
            it("does not execute the callback", function(){
                expect(callback).not.toHaveBeenCalled();
                expect(errorReporter).toHaveBeenCalledWith("An error occurred while attempting the requested change.");
            });
        });

        describe("when the request comes back with failure", function(){
            beforeEach(function(){
                jest.spyOn($j, "post").mockReturnValue(resolved({ret: false, msg: "The teacher is not available"}));
                a.send_request('ajax_schedule_class', {}, callback, errorReporter);
            });
            it("does not execute the callback", function(){
                expect(callback).not.toHaveBeenCalled();
                expect(errorReporter).toHaveBeenCalledWith("The teacher is not available");
            });
        });

        describe("when the request comes back with success", function(){
            beforeEach(function(){
                jest.spyOn($j, "post").mockReturnValue(resolved({ret: true}));
                a.send_request('ajax_schedule_class', {}, callback, errorReporter);
            });
            it("executes the callback", function(){
                expect(callback).toHaveBeenCalled();
                expect(errorReporter).not.toHaveBeenCalled();
            });
        });
    });

});
