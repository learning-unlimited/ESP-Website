
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
                qsd_inline_update(qsd_url, edit_id, data);
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

function qsd_inline_upload(qsd_url, edit_id)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + edit_id).className = "hidden";
    document.getElementById("inline_qsd_" + edit_id).className = "qsd_view_visible";

    var content = document.getElementById("qsd_content_" + edit_id).value;
    var postdata = {cmd: "update", url: qsd_url, data: content};
    qsd_send_command(qsd_url, edit_id, postdata);
}

function qsd_inline_update(qsd_url, edit_id, data)
{
    var postdata = JSON.parse(data);
    document.getElementById("inline_qsd_" + edit_id).innerHTML = postdata.content;
}


