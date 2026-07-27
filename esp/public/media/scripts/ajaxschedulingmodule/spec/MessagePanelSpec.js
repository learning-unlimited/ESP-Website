describe("MessagePanel", function() {
    var mp;
    beforeEach(function() {
        mp = new MessagePanel($j("<div>"));
    });

    afterEach(function() {
        $j(".scheduler-toast").remove();
    });

    it("should be able to be initialized with an initial message", function() {
        mp2 = new MessagePanel($j("<div>"), "Hello, World!");
        expect(mp2.el[0].innerHTML).toEqual("<p>Hello, World!</p>");
    });

    describe("addMessage", function() {
        it("should add a new message", function() {
            mp.addMessage("new message");
            expect(mp.el[0].innerHTML).toEqual("<p>new message</p>");
        });

        it("should show error messages as a toast", function() {
            mp.addMessage("new error", "red");
            expect($j("body .scheduler-toast").length).toEqual(1);
            expect($j("body .scheduler-toast").text()).toEqual("new error");
        });
    });

    describe("hide", function() {
        it("should add the ui-helper-hidden class", function() {
            mp.hide();
            expect(mp.el.hasClass("ui-helper-hidden")).toBeTrue;
        });
    });

    describe("show", function() {
        it("should remove the ui-helper-hidden class", function() {
            mp.hide();
            mp.show();
            expect(mp.el.hasClass("ui-helper-hidden")).toBeFalse;
        });
    });

});
