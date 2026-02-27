
//  Straight forward functions for Ajax QSD editing

function post_encode(data)
{
    //  Convert a Javascript object to x-www-form-urlencoded format.
    var result = '';
    var i = 0;
    for (key in data)
    {
        if (key != 'toJSON')
        {
            if (i != 0) result += '&';
            result += key + '=' + encodeURIComponent(data[key]);
            i++;
        }
    }
    return result
}

function qsd_inline_edit(qsd_url, edit_id)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + edit_id).className = "qsd_edit_visible";
    $j("#inline_edit_msg_" + edit_id).hide();
    document.getElementById("qsd_content_" + edit_id).focus();
    document.getElementById("inline_qsd_" + edit_id).className = "hidden";
}

function qsd_send_command(qsd_url, edit_id, postdata)
{
    //Refresh the csrf token if needed
    refresh_csrf_cookie();
    postdata.csrfmiddlewaretoken = csrf_token();

    $j.post("/admin/ajax_qsd", post_encode(postdata), function(data, status)
    {
        if (status == "success")
        {
            if (data)
            {
                qsd_inline_update(qsd_url, edit_id, data,
                    "Saved! Now reloading...", 'green', 'glyphicon-ok');
                window.location.reload(true); // bust the cache
            }
        }
        else
        {
            alert("Abnormal Status: " + status + "\nData: " + data);
        }
    }).fail(function(request, jquery_status, http_status)
    {
        alert(jquery_status + ": " + http_status + "\n" + request.responseText);
    });

    $j.post("/varnish/purge_page", { page: $j(location).attr('pathname'), csrfmiddlewaretoken: csrf_token()});
}

function qsd_send_preview(qsd_url, edit_id, postdata)
{
    //Refresh the csrf token if needed
    refresh_csrf_cookie();
    postdata.csrfmiddlewaretoken = csrf_token();

    $j.post("/admin/ajax_qsd_preview", post_encode(postdata), function(data, status) {
        if (status === "success") {
            if (data) {
                qsd_inline_update(qsd_url, edit_id, data,
                    "This is a preview &mdash; your changes have not been saved! Click here to edit the text.",
                    'red', 'glyphicon-alert');
            }
        } else {
            alert("Abnormal Status: " + status + "\nData: " + data);
        }
    }).fail(function(request, jquery_status, http_status) {
        alert(jquery_status + ": " + http_status + "\n" + request.responseText);
    });
}

function qsd_inline_finish(qsd_url, edit_id, action)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + edit_id).className = "hidden";
    $j("#inline_edit_msg_" + edit_id).show();
    document.getElementById("inline_qsd_" + edit_id).className = "qsd_view_visible";

    if (action) {
        var content = document.getElementById("qsd_content_" + edit_id).value;
        if (action === 'save') {
            var postdata = {cmd: "update", url: qsd_url, data: content};
            qsd_send_command(qsd_url, edit_id, postdata);
        } else {
            qsd_send_preview(qsd_url, edit_id, {data: content});
        }
    }
}

function qsd_inline_update(qsd_url, edit_id, data, message, color, glyphicon) {
    var postdata = JSON.parse(data);
    document.getElementById("inline_qsd_" + edit_id).innerHTML = postdata.content;
    var $msgElement = $j("#inline_edit_msg_" + edit_id);
    $msgElement.children('.inline_edit_msg_text').html(message);
    $msgElement.css('color', color);
    $msgElement.children('.glyphicon').prop('class', 'glyphicon ' + glyphicon);
}


