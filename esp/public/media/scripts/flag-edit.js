function submitFlagForm (event) {
    console.log("submit");
    var form = $j(this)
    var data = form.serialize();
    $j.post(form.attr("action"), data, function (data) {
        form.parents("div.flag-detail").replaceWith(data);
    })
    event.preventDefault();
}

function addFlag (event) {
    var flagExtra = $j(event.target).parents(".fqr-class").find(".flag-extra").last();
    flagExtra.clone().show().insertBefore(flagExtra);
}

function removeFlag (url, id) {
    var div1 = $j("div#flag-detail-"+id);
    var div2 = $j("span#fqr-flag-header-"+id);
    $j.post(url, {'csrfmiddlewaretoken': csrf_token(), 'id' : id}, function () { div1.hide(); div2.hide(); });
}

$j(document).on("submit", "form.flag-form", submitFlagForm)
$j(document).on("click", "button.add-flag", addFlag)
