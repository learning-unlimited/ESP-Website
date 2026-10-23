describe("Scheduler", function(){
    var s;

    beforeEach(function(){
        // The ChangelogFetcher asks the server for the latest changelog index
        jest.spyOn($j, "getJSON").mockImplementation(function(url, callback){
            callback({latest_index: 11}, "success");
        });
        var data = {
            schedule_assignments: {},
            rooms: {},
            timeslots: {},
            lunch_timeslots: [],
            sections: {},
            section_details: {},
            categories: {},
            teachers: {},
            moderators: {},
            resource_types: {},
        };
        s = new Scheduler(data, $j("<div/>"), $j("<div/>"), $j("<div/>"), $j("<div/>"), $j("<div/>"), $j("<div/>"), 12345678);
    });

    it("should have a directory and a matrix", function(){
        expect(s.directory).toBeInstanceOf(Directory);
        expect(s.matrix).toBeInstanceOf(Matrix);
    });

    it("should have a changelogFetcher with the right initial index", function(){
        expect(s.changelogFetcher).toBeInstanceOf(ChangelogFetcher);
        expect($j.getJSON).toHaveBeenCalledWith('ajax_schedule_last_changed', expect.any(Function));
        expect(s.changelogFetcher.last_applied_index).toEqual(11)
    })

    describe("render", function(){
        it("calls render on the directory and matrix",  function(){
            jest.spyOn(s.directory, "render").mockImplementation(function(){});
            jest.spyOn(s.matrix, "render").mockImplementation(function(){});
            jest.spyOn(s.changelogFetcher, "pollForChanges").mockImplementation(function(){});
            s.render();
            expect(s.directory.render).toHaveBeenCalled();
            expect(s.matrix.render).toHaveBeenCalled();
        });

        it("starts the changelog fetcher", function(){
            jest.spyOn(s.changelogFetcher, "pollForChanges").mockImplementation(function(){});

            s.render()
            expect(s.changelogFetcher.pollForChanges).toHaveBeenCalledWith(12345678)
        })
    });
});
