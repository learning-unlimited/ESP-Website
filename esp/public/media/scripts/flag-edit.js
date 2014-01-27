function submitFlagForm (event) {
    console.log("submit");
    var form = $j(this)
    var data = form.serialize();
    $j.post(form.attr("action"), data, function (data) {
        form.parents("div.flag-detail").replaceWith(data);
        $j("button.add-flag").show();
    })
    event.preventDefault();
}

function addFlag (event) {
    $j("#flag-extra").clone().attr("id","flag-new").show().insertBefore(this);
    $j(this).hide();
}

function removeFlag (url, id) {
    var div = $j("div#flag-detail-"+id);
    $j.post(url, {'csrfmiddlewaretoken': csrf_token(), 'id' : id}, function () { div.hide(); });
}

$j(document).on("submit", "form.flag-form", submitFlagForm)
$j(document).on("click", "button.add-flag", addFlag)
