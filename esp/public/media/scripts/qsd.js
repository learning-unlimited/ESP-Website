
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
    var request = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject("MSXML2.XMLHTTP.3.0");
    request.open("POST", "/admin/ajax_qsd/", true);
    request.setRequestHeader("Content-Type", "application/x-www-form-urlencoded;charset=utf-8");
    request.onreadystatechange = function ()
    {
        //  alert("Received " + request.readyState + ", " + request.status)
        if (request.readyState == 4)
        {
            if (request.status == 200)
            {
                if (request.responseText)
                {
                    qsd_inline_update(qsd_id, request.responseText);
                }
            }
            else
            {
                alert(request.responseText);
            }
        }
        /*
        else
        {
            new_window = window.open("", "ESPError");
            new_window.document.write(request.responseText);
        }
        //  */
    };
    var poststring = post_encode(postdata);
    //  alert("Sending: " + poststring);
    request.send(poststring);
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

function qsd_inline_create(qsd_name, anchor_id)
{
    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + qsd_name).className = "qsd_edit_hidden";
    document.getElementById("inline_qsd_" + qsd_name).className = "qsd_view_visible";

    var content = document.getElementById("qsd_content_" + qsd_name).value;
    var postdata = {cmd: "create", name: qsd_name, data: content, anchor: anchor_id};
    qsd_send_command(qsd_name, postdata);
}

function qsd_inline_update(qsd_id, data)
{
    var postdata = JSON.parse(data);
    document.getElementById("inline_qsd_" + qsd_id).innerHTML = postdata.content;
}


