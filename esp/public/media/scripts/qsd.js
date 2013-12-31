
//  Straight forward functions for Ajax QSD editing

/*  Short string hash function of a string value    */
function qsd_url_hash(value)
{
    var hash = 0;
    if (value.length == 0) return hash;
    for (var i = 0; i < value.length; i++) {
        var character = value.charCodeAt(i);
        hash = ((hash << 5) - hash) + character;
        hash = hash & ((1 << 31) - 1); // Convert to 32bit signed positive integer
    }
    var strbase = hash.toString(16);
    while (strbase.length < 8)
        strbase = '0' + strbase;
    return strbase;
}

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

function qsd_inline_edit(qsd_url)
{
    //  Switch the visibility of the edit and view areas.
    var edit_id = qsd_url_hash(qsd_url);
    document.getElementById("inline_edit_" + edit_id).className = "qsd_edit_visible";
    document.getElementById("qsd_content_" + edit_id).focus();
    document.getElementById("inline_qsd_" + edit_id).className = "qsd_view_hidden";
}

function qsd_send_command(qsd_url, postdata)
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
                qsd_inline_update(qsd_url, data);
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

    $j.post("/cache/varnish_purge", { page: $j(location).attr('pathname'), csrfmiddlewaretoken: csrf_token()});
}

function qsd_inline_upload(qsd_url)
{
    var edit_id = qsd_url_hash(qsd_url);

    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + edit_id).className = "qsd_edit_hidden";
    document.getElementById("inline_qsd_" + edit_id).className = "qsd_view_visible";

    var content = document.getElementById("qsd_content_" + edit_id).value;
    var postdata = {cmd: "update", url: qsd_url, data: content};
    qsd_send_command(qsd_url, postdata);
}

function qsd_inline_create(qsd_url)
{
    var edit_id = qsd_url_hash(qsd_url);
    
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + edit_id).className = "qsd_edit_hidden";
    document.getElementById("inline_qsd_" + edit_id).className = "qsd_view_visible";

    var content = document.getElementById("qsd_content_" + edit_id).value;
    var postdata = {cmd: "create", url: qsd_url, data: content};
    qsd_send_command(qsd_url, postdata);
}

function qsd_inline_update(qsd_url, data)
{
    var edit_id = qsd_url_hash(qsd_url);
    var postdata = JSON.parse(data);
    console.log("received update");
    document.getElementById("inline_qsd_" + edit_id).innerHTML = postdata.content;
}


