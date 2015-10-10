describe("Scheduler", function(){
    var s;

    beforeEach(function(){
        s = new Scheduler({schedule_assignments: {}, rooms: {}, timeslots: {}, sections: {}}, $j("<div/>"), $j("<div/>"), $j("<div/>"), $j("<div/>"), $j("<div/>"), 11, 12345678);
    });

    it("should have a directory and a matrix", function(){
        expect(s.directory).toBeDefined();
        expect(s.matrix).toBeDefined();
    });

    it("should have a changelogFetcher with the right initial index", function(){
        expect(s.changelogFetcher).toBeDefined()
        expect(s.changelogFetcher.last_applied_index).toEqual(11)
    })

    describe("render", function(){
        it("calls render on the directory and matrix",  function(){
            spyOn(s.directory, "render");
            spyOn(s.matrix, "render");
            s.render();
            expect(s.directory.render).toHaveBeenCalled();
            expect(s.matrix.render).toHaveBeenCalled();
        });

        it("starts the changelog fetcher", function(){
            spyOn(s.changelogFetcher, "pollForChanges")

            s.render()
            expect(s.changelogFetcher.pollForChanges).toHaveBeenCalled()

            args = s.changelogFetcher.pollForChanges.argsForCall[0]
            expect(args[0]).toEqual(12345678)
        })
    });
});
