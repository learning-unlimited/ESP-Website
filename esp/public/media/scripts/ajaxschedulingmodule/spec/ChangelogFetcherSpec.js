const { FakeApiClient } = require("./FakeApiClient");
const { generateFakeMatrix } = require("./FakeMatrix");

describe("ChangelogFetcher", function() {
    var c;

    // As stored by AJAXChangeLogEntry, room_name holds the room's id
    var changelog_entry = {
        id: 2,
        index: 2,
        is_scheduling: true,
        room_name: "102",
        timeslots: [ 3 ],
    };

    var unschedule_changelog_entry = {
        timeslots: [],
        room_name: "",
        is_scheduling: true,
        id: 1,
        index: 3,
    };

    var changelog = {
        changelog: [changelog_entry, unschedule_changelog_entry]
    };

    beforeEach(function() {
        // The constructor asks the server for the latest changelog index
        jest.spyOn($j, "getJSON").mockImplementation(function(url, callback){
            callback({latest_index: 32}, "success");
        });
        c = new ChangelogFetcher(generateFakeMatrix(), new FakeApiClient());
    });

    it("should set the last_applied_index", function(){
        expect(c.last_applied_index).toEqual(32);
    });

    describe("getChanges", function(){
        it("calls the API client", function(){
            jest.spyOn(c.api_client, "get_change_log").mockImplementation(function(){});
            c.getChanges();

            expect(c.api_client.get_change_log).toHaveBeenCalled();

            var args = c.api_client.get_change_log.mock.calls[0];
            expect(args[0]).toEqual(c.last_applied_index);
        });
    });

    describe("pollForChanges", function(){
        it("sets an interval", function(){
            jest.spyOn(window, "setInterval").mockReturnValue(1);
            c.pollForChanges(1234567);

            expect(window.setInterval).toHaveBeenCalled();
            var args = window.setInterval.mock.calls[0];
            expect(args[1]).toEqual(1234567);
        });

        it("fetches the changes immediately", function(){
            jest.spyOn(window, "setInterval").mockReturnValue(1);
            jest.spyOn(c, "getChanges");
            c.pollForChanges(1234567);
            expect(c.getChanges).toHaveBeenCalled();
        });
    });

    describe("applyChangeLog", function(){
        it("schedules the classes locally", function(){
            jest.spyOn(c.matrix.sections, "scheduleSectionLocal").mockImplementation(function(){});
            c.applyChangeLog(changelog);
            expect(c.matrix.sections.scheduleSectionLocal).toHaveBeenCalled();

            var args = c.matrix.sections.scheduleSectionLocal.mock.calls[0];
            var s = c.matrix.sections.getById(2);
            expect(args[0]).toEqual(s);
            expect(args[1]).toEqual(102);
            expect(args[2]).toEqual([3]);
        });

        it("unschedules the classes locally", function(){
            jest.spyOn(c.matrix.sections, "unscheduleSectionLocal").mockImplementation(function(){});
            c.applyChangeLog(changelog);
            expect(c.matrix.sections.unscheduleSectionLocal).toHaveBeenCalled();

            var args = c.matrix.sections.unscheduleSectionLocal.mock.calls[0];
            var s1 = c.matrix.sections.getById(1);
            expect(args[0]).toEqual(s1);
        });

        it("updates the last fetched number", function(){
            c.applyChangeLog(changelog);
            expect(c.last_applied_index).toEqual(3);
        });

        it("updates the matrix", function(){
            c.applyChangeLog(changelog);
            expect(c.matrix.getCell(102, 3).section).toBe(c.matrix.sections.getById(2));
            expect(c.matrix.getCell(101, 3).section).toBeNull();
        });

        describe("when the server commands a reload", function(){
            var reload_response = {
                other: [{ command: "reload", earliest_index: 99, latest_index: 105, time: 1234567890 }]
            };

            afterEach(function(){
                $j("#changelog-reload-notice").remove();
            });

            it("invokes showReloadNotification", function(){
                jest.spyOn(c, "showReloadNotification").mockImplementation(function(){});
                c.applyChangeLog(reload_response);
                expect(c.showReloadNotification).toHaveBeenCalled();
            });

            it("does not process changelog entries on reload", function(){
                jest.spyOn(c.matrix.sections, "scheduleSectionLocal").mockImplementation(function(){});
                jest.spyOn(c.matrix.sections, "unscheduleSectionLocal").mockImplementation(function(){});
                c.applyChangeLog(reload_response);
                expect(c.matrix.sections.scheduleSectionLocal).not.toHaveBeenCalled();
                expect(c.matrix.sections.unscheduleSectionLocal).not.toHaveBeenCalled();
            });

            it("does not throw when changelog key is missing", function(){
                expect(function(){
                    c.applyChangeLog({ other: [{ time: 1234567890 }] });
                }).not.toThrow();
            });

            it("stops polling when reload is requested", function(){
                jest.spyOn(window, "clearInterval").mockImplementation(function(){});
                c.pollInterval = 4242;
                c.showReloadNotification();
                expect(window.clearInterval).toHaveBeenCalledWith(4242);
                expect(c.pollInterval).toBeNull();
            });

            it("only shows the notification banner once", function(){
                c.showReloadNotification();
                c.showReloadNotification();
                expect($j("#changelog-reload-notice").length).toEqual(1);
            });
        });
    });
});
