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
        if (data.warning) {
            var overlay = $j('<div class="flag-warning-overlay"></div>')
                .css({
                    'position': 'fixed',
                    'top': '0',
                    'left': '0',
                    'right': '0',
                    'bottom': '0',
                    'background': 'rgba(0,0,0,0.5)',
                    'z-index': '99998',
                    'display': 'flex',
                    'align-items': 'center',
                    'justify-content': 'center'
                });
            var box = $j('<div></div>')
                .css({
                    'background': '#fff',
                    'border-left': '6px solid #cc3300',
                    'padding': '24px 32px',
                    'border-radius': '8px',
                    'max-width': '500px',
                    'box-shadow': '0 8px 32px rgba(0,0,0,0.3)',
                    'text-align': 'center'
                })
                .html('<div style="font-size:36px;margin-bottom:12px;">&#9888;</div>' +
                       '<div style="font-size:16px;font-weight:bold;color:#cc3300;margin-bottom:8px;">Email Notification Failed</div>' +
                       '<div style="font-size:14px;color:#333;">' + data.warning + '</div>' +
                       '<button class="flag-warning-dismiss" style="margin-top:16px;padding:8px 24px;background:#cc3300;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:14px;">OK</button>');
            overlay.append(box);
            $j('body').append(overlay);
            overlay.find('.flag-warning-dismiss').on('click', function() {
                overlay.fadeOut(300, function() { overlay.remove(); });
            });
        }
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
