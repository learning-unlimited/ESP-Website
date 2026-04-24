describe("HistoryPanel", function() {
    var container;
    var clearBtn;
    var panel;

    beforeEach(function() {
        container = $j("<ul/>");
        clearBtn = $j("<button type='button'/>");
        panel = new HistoryPanel(container, clearBtn);
    });

    it("starts empty with a placeholder row", function() {
        expect(container.find(".scheduler-history-empty").length).toEqual(1);
    });

    it("addAction appends an entry and increments the stack", function() {
        panel.addAction("Test action", function(endUndo) {
            endUndo();
        });
        expect(panel.items.length).toEqual(1);
        expect(container.find(".scheduler-history-row").length).toEqual(1);
    });

    it("does not add actions while undoing", function() {
        panel.addAction("first", function() {});
        panel.undoing = true;
        panel.addAction("second", function(endUndo) {
            endUndo();
        });
        expect(panel.items.length).toEqual(1);
        panel.undoing = false;
    });

    it("runUndoLatest invokes only the latest undo and clears undoing after endUndo", function() {
        var order = [];
        panel.addAction("older", function(endUndo) {
            order.push("older");
            endUndo();
        });
        panel.addAction("newer", function(endUndo) {
            order.push("newer");
            endUndo();
        });
        panel.runUndoLatest();
        expect(order).toEqual(["newer"]);
        expect(panel.items.length).toEqual(1);
        expect(panel.undoing).toEqual(false);
    });

    it("supports multiple sequential undos without stale entry references", function() {
        var order = [];
        panel.addAction("a", function(endUndo) {
            order.push("a");
            endUndo();
        });
        panel.addAction("b", function(endUndo) {
            order.push("b");
            endUndo();
        });
        panel.addAction("c", function(endUndo) {
            order.push("c");
            endUndo();
        });
        panel.runUndoLatest();
        panel.runUndoLatest();
        panel.runUndoLatest();
        expect(order).toEqual(["c", "b", "a"]);
        expect(panel.items.length).toEqual(0);
    });

    it("clear removes all entries", function() {
        panel.addAction("x", function(endUndo) {
            endUndo();
        });
        panel.clear();
        expect(panel.items.length).toEqual(0);
        expect(container.find(".scheduler-history-empty").length).toEqual(1);
    });

    it("drops oldest entries when exceeding MAX_ITEMS", function() {
        var i;
        for (i = 0; i < panel.MAX_ITEMS + 3; i++) {
            panel.addAction("n" + i, function(endUndo) {
                endUndo();
            });
        }
        expect(panel.items.length).toEqual(panel.MAX_ITEMS);
        expect(panel.items[0].description).toEqual("n3");
    });

    it("clear button clears the panel", function() {
        panel.addAction("y", function(endUndo) {
            endUndo();
        });
        clearBtn.trigger("click");
        expect(panel.items.length).toEqual(0);
    });
});
