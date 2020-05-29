function submitAssignmentForm (event) {
    console.log("submit");
    var form = $j(this)
    var data = form.serialize();
    $j.post(form.attr("action"), data, function (data) {
        form.parents("div.fqr-class").find("div.fqr-class-assignments").append(data.assignment_name);
        form.parents("div.assignment-detail").replaceWith(data.assignment_detail);
    }, 'json')
    event.preventDefault();
}

function addAssignment (event) {
    var flagExtra = $j(event.target).parents(".fqr-class").find(".assignment-extra").last();
    flagExtra.clone().show().insertBefore(flagExtra);
}

function removeAssignment (url, id) {
    var div1 = $j("div#assignment-detail-"+id);
    var div2 = $j("span#fqr-assignment-header-"+id);
    $j.post(url, {'csrfmiddlewaretoken': csrf_token(), 'id' : id}, function () { div1.hide(); div2.hide(); });
}

$j(document).on("submit", "form.assignment-form", submitAssignmentForm)
$j(document).on("click", "button.add-assignment", addAssignment)
