function updateNode () {
    // Update the tree to reflect a change in a type selector.
    var typeSelector = $j(this);
    var value = typeSelector.val();
    var flagSelector = typeSelector.siblings(".fqb-flag-list");
    var flagDetailsSelector = typeSelector.siblings(".fqb-flag-details");
    var statusSelector = typeSelector.siblings(".fqb-status-list");
    var categorySelector = typeSelector.siblings(".fqb-category-list");
    var ul = typeSelector.siblings("ul");
    function hideAll () {
        // Hide all conditionally-displayed selectors.
        flagSelector.hide();
        flagDetailsSelector.hide();
        statusSelector.hide();
        categorySelector.hide();
        ul.hide();
    }
    if (value.indexOf("flag") > -1) {
        // The user has picked a single flag, we need to show the flag selector
        hideAll();
        flagSelector.show();
        flagDetailsSelector.show();
        flagDetailsSelector.find(".datetime-input").datetimepicker();
    } else if (value.indexOf("status") > -1) {
        // The user has picked a single status, we need to show the status selector
        hideAll();
        statusSelector.show();
    } else if (value.indexOf("category") > -1) {
        // The user has picked a single category, we need to show the category selector
        hideAll();
        categorySelector.show();
    } else if (value.length > 0) {
        // The user has picked a subexpression, we need to build it
        hideAll();
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
        hideAll();
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

function timeUpdate(obj, node, prefix) {
    span = node.find("."+prefix+"time-options");
    if (span.children(".checkbox").prop("checked")) {
        obj[prefix + "_when"] = span.children(".fqb-flag-detail-select").val();
        obj[prefix + "_time"] = span.children(".datetime-input").val();
    }
}


function buildSingleObject (node, objectType, value) {
    var objectValue = node.children(".fqb-"+objectType+"-list").val();
    if (objectType === "flag") {
        // Instead of just the flag id, we want to return an object, because we
        // could be doing a more complex constraint.
        if (objectValue) {
            objectValue = { id: objectValue };
        } else {
            objectValue = {};
        }
        var detailDiv = node.children(".fqb-flag-details");
        timeUpdate(objectValue, node, "modified");
        timeUpdate(objectValue, node, "created");
        if ($j.isEmptyObject(objectValue)) {
            node.addClass("bad-node");
            throw new BuildQueryError("No flag details.");
        } else {
            var obj = { type: value, value: objectValue };
            return obj;
        }
    } else if (objectValue.length) {
        // objectValue is a nonempty string or a nonempty object.
        var obj = { type: value, value: objectValue };
        return obj;
    } else {
        // But they didn't pick a thing-- bad user!
        node.addClass("bad-node");
        throw new BuildQueryError("No "+objectType);
    }
}

function buildObject (node) {
    // Recursively builds the javascript object to be converted to JSON.
    if ( node.is("div") || node.is("li") ) {
        // We want to build an object
        var value = node.children(".fqb-type").val();
        if (value.indexOf("flag") > -1) {
            // We have just a single flag
            return buildSingleObject(node, "flag", value)
        } else if (value.indexOf("status") > -1) {
            // We have just a single status 
            return buildSingleObject(node, "status", value)
        } else if (value.indexOf("category") > -1) {
            // We have just a single category 
            return buildSingleObject(node, "category", value)
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
