describe("MessagePanel", function () {
    var mp;
    beforeEach(function () {
        mp = new MessagePanel($j("<div>"));
    });

    afterEach(function () {
        $j(".scheduler-toast").remove();
    });

    it("should be able to be initialized with an initial message", function () {
        mp2 = new MessagePanel($j("<div>"), "Hello, World!");
        expect(mp2.el[0].innerHTML).toEqual("");
    });

    describe("addMessage", function () {
        it("should show error messages as a toast", function () {
            mp.addMessage("new error", "error");
            expect($j("body .scheduler-toast").length).toEqual(1);
            expect($j("body .scheduler-toast").text()).toEqual("new error");
            expect(mp.el[0].innerHTML).toEqual("");
        });

        it("should show success messages as a green toast", function () {
            mp.addMessage("new success", "success");
            expect($j("body .scheduler-toast").length).toEqual(1);
            expect($j("body .scheduler-toast").text()).toEqual("new success");
            expect($j("body .scheduler-toast").hasClass("scheduler-toast-success")).toBeTrue;
            expect(mp.el[0].innerHTML).toEqual("");
        });

        it("should not add a new text message", function () {
            mp.addMessage("new message");
            expect(mp.el[0].innerHTML).toEqual("");
        });
    });

    describe("hide", function () {
        it("should add the ui-helper-hidden class", function () {
            mp.hide();
            expect(mp.el.hasClass("ui-helper-hidden")).toBeTrue;
        });
    });

    describe("show", function () {
        it("should remove the ui-helper-hidden class", function () {
            mp.hide();
            mp.show();
            expect(mp.el.hasClass("ui-helper-hidden")).toBeFalse;
        });
    });

});
