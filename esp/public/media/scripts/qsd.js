
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

function qsd_inline_edit(qsd_id)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + qsd_id).className = "qsd_edit_visible";
    document.getElementById("qsd_content_" + qsd_id).focus();
    document.getElementById("inline_qsd_" + qsd_id).className = "qsd_view_hidden";
}

function qsd_send_command(qsd_id, postdata)
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
                qsd_inline_update(qsd_id, data);
            }
        }
        else
        {
            alert("Error! Status: " + status);
            alert("Data: " + data);
        }
    });

    $j.post("/cache/varnish_purge", { page: $j(location).attr('pathname'), csrfmiddlewaretoken: csrf_token()});
}

function qsd_inline_upload(qsd_id)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + qsd_id).className = "qsd_edit_hidden";
    document.getElementById("inline_qsd_" + qsd_id).className = "qsd_view_visible";

    var content = document.getElementById("qsd_content_" + qsd_id).value;
    var postdata = {cmd: "update", id: qsd_id, data: content};
    qsd_send_command(qsd_id, postdata);
}

function qsd_inline_create(qsd_name)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + qsd_name).className = "qsd_edit_hidden";
    document.getElementById("inline_qsd_" + qsd_name).className = "qsd_view_visible";

    var content = document.getElementById("qsd_content_" + qsd_name).value;
    var postdata = {cmd: "create", url: qsd_name, data: content};
    qsd_send_command(qsd_name, postdata);
}

function qsd_inline_update(qsd_id, data)
{
    var postdata = JSON.parse(data);
    document.getElementById("inline_qsd_" + qsd_id).innerHTML = postdata.content;
}


