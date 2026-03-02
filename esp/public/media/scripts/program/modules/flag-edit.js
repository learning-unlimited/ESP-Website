function submitFlagForm (event) {
    console.log("submit");
    var form = $j(this)
    var data = form.serialize();
    var $oldDetail = form.parents("div.flag-detail");
    var wasVisible = $oldDetail.is(":visible");
    $j.post(form.attr("action"), data, function (data) {
        if (data.flag_name) {
            $oldDetail.parents("div.fqr-class").find("div.fqr-class-flags").append(data.flag_name);
        }
        var $newDetail = $j(data.flag_detail);
        if (wasVisible) { $newDetail.show(); }
        $oldDetail.replaceWith($newDetail);
    }, 'json')
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

function resolveFlag (url, id, btn, action) {
    var $btn = $j(btn);
    $btn.prop('disabled', true);
    var csrfToken = $btn.closest('form').find('input[name=csrfmiddlewaretoken]').val();
    var wasVisible = $j("div#flag-detail-" + id).is(":visible");
    var $oldHeader = $j("span#fqr-flag-header-" + id);
    var hadActive = $oldHeader.hasClass('active');
    $j.post(url + id + '/', {'csrfmiddlewaretoken': csrfToken, 'action': action}, function (data) {
        var $newDetail = $j(data.flag_detail);
        if (wasVisible) { $newDetail.show(); }
        $j("div#flag-detail-" + id).replaceWith($newDetail);
        var $newHeader = $j(data.flag_name);
        if (!hadActive) { $newHeader.removeClass('active'); }
        $oldHeader.replaceWith($newHeader);
    }, 'json').fail(function () {
        $btn.prop('disabled', false);
    });
}

$j(document).on("submit", "form.flag-form", submitFlagForm)
$j(document).on("click", "button.add-flag", addFlag)
