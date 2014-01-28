function updateNode () {
    // Update the tree to reflect a change in a type selector.
    var typeSelector = $j(this);
    var value = typeSelector.val();
    var flagSelector = typeSelector.siblings(".fqb-flags");
    var ul = typeSelector.siblings("ul");
    if (value.indexOf("flag") > -1) {
        // The user has picked a single flag, we need to show the flag selector
        flagSelector.show();
        ul.hide();
    } else if (value.length > 0) {
        // The user has picked a subexpression, we need to build it
        flagSelector.hide();
        if (ul.length > 0) {
            // We can just unhide an existing ul
            ul.show();
        } else {
            // We have to create one
            var extraUL = $j(".fqb-extra ul");
            extraUL.clone().appendTo(typeSelector.parent());
        }
    } else {
        // The user has selected nothing, we need to hide everything
        flagSelector.hide();
        ul.hide();
    }
}

function addLine () {
    var addButton = $j(this);
    var extraLI = $j(".fqb-extra li.fqb-line");
    extraLI.clone().insertBefore(addButton.parent());
}

function deleteLine () {
    $j(this).parent().remove();
}

function preSubmit (event) {
    // Builds the JSON and puts it in the form hidden field
    $j(".bad-node").removeClass("bad-node");
    var root = $j(".fqb-initial-line");
    try {
        var object = buildObject(root);
    } catch (e) {
        alert("There was an error, recheck your query.");
        event.preventDefault();
        if (e.name !== "BuildQueryError") {
            // If the error was not ours, rethrow it so it hits the error reporter.
            throw e
        } else {
            // If it was ours, just return.
            return;
        }
    }
    // If there was no error, set the hidden field and proceed.
    var stringified = JSON.stringify(object);
    $j(".fqb-form input.query-json").val(stringified);
    return;
}

function BuildQueryError(message) {
    this.message = message;
    this.name = "BuildQueryError";
}


function buildObject (node) {
    // Recursively builds the javascript object to be converted to JSON.
    if ( node.is("div") || node.is("li") ) {
        // We want to build an object
        var value = node.children(".fqb-type").val();
        if (value.indexOf("flag") > -1) {
            // We have just a single flag
            var flag = node.children(".fqb-flags").val();
            if (flag.length > 0) {
                var obj = { type: value, value: flag };
                return obj;
            } else {
                // But they didn't pick a flag -- bad user!
                node.addClass("bad-node");
                throw new BuildQueryError("No flag");
            }
        } else if (value.length > 0) {
            // We have a subexpression -- recurse
            var ul = node.children("ul");
            var rec = buildObject(ul);
            var obj = { type: value, value: rec };
            return obj;
        } else {
            // We have nothing -- bad user!
            node.addClass("bad-node");
            throw new BuildQueryError("No type");
        }
    } else {
        // We want to build a list
        var children = node.children(".fqb-line");
        var obj = [];
        children.each(function (i) {
            var rec = buildObject($j(children[i]));
            obj.push(rec);
        })
        if (obj.length > 0) {
            return obj;
        } else {
            node.addClass("bad-node");
            throw new BuildQueryError("Empty list");
        }
    }
}


function loadFQB () {
    // Called when the document is ready
    $j(document).on("change","select.fqb-type",updateNode);
    $j(document).on("click","button.fqb-add",addLine);
    $j(document).on("click","button.fqb-delete",deleteLine);
    $j(document).on("submit",".fqb-form form",preSubmit);
    $j(".fqb-initial-line select").val("");
}

$j(document).ready(loadFQB);
