/**
 * Session-only list of recent scheduling actions with undo (most recent only).
 *
 * @param containerEl jQuery element for the <ul> list
 * @param clearButtonEl optional jQuery element for "Clear" (wired to clear())
 */
function HistoryPanel(containerEl, clearButtonEl) {
    this.container = containerEl;
    this.MAX_ITEMS = 20;
    this.items = [];
    this.undoing = false;

    if (clearButtonEl && clearButtonEl.length) {
        clearButtonEl.on("click", function() {
            this.clear();
        }.bind(this));
    }
    this.render();
}

HistoryPanel.prototype.clear = function() {
    this.items = [];
    this.render();
};

/**
 * @param description string shown in the list
 * @param undoFn function(endUndo) must call endUndo() when the async undo finishes (success or error)
 */
HistoryPanel.prototype.addAction = function(description, undoFn) {
    if (this.undoing) {
        return;
    }
    this.items.push({ description: description, undo: undoFn });
    if (this.items.length > this.MAX_ITEMS) {
        this.items.shift();
    }
    this.render();
};

HistoryPanel.prototype.render = function() {
    var self = this;
    this.container.empty();
    var n = this.items.length;
    if (n === 0) {
        this.container.append(
            $j("<li/>")
                .addClass("scheduler-history-empty")
                .text("No actions yet. Schedule or edit a class to see entries here.")
        );
        return;
    }
    for (var i = n - 1; i >= 0; i--) {
        var item = this.items[i];
        var isNewest = i === n - 1;
        var li = $j("<li/>").addClass("scheduler-history-row");
        if (isNewest) {
            li.addClass("scheduler-history-row--latest");
        }
        var span = $j("<span/>")
            .addClass("scheduler-history-desc")
            .text(item.description);
        var btn = $j("<button type='button'/>")
            .addClass("scheduler-history-undo")
            .text("Undo");
        if (!isNewest) {
            btn.prop("disabled", true);
            btn.attr("title", "Undo the most recent action first");
        }
        (function(entry) {
            btn.on("click", function() {
                if (!isNewest) {
                    return;
                }
                self.runUndo(entry);
            });
        })(item);
        li.append(span).append(btn);
        this.container.append(li);
    }
};

HistoryPanel.prototype.runUndo = function(item) {
    var self = this;
    if (this.items.length === 0 || this.items[this.items.length - 1] !== item) {
        return;
    }
    this.items.pop();
    this.render();
    this.undoing = true;
    item.undo(function() {
        self.undoing = false;
    });
};
