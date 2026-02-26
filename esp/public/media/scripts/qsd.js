
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


//  Version history functions

function qsd_toggle_history(qsd_url, edit_id)
{
    var $panel = $j("#qsd_history_panel_" + edit_id);
    if ($panel.is(":visible")) {
        $panel.slideUp(200);
        return;
    }

    $panel.html('<p style="text-align:center; padding:12px;"><span class="glyphicon glyphicon-refresh"></span> Loading history...</p>');
    $panel.slideDown(200);

    $j.get("/admin/ajax_qsd_history", { url: qsd_url }, function(data) {
        var versions = data.versions;
        if (versions.length === 0) {
            $panel.html('<p style="padding:8px;">No version history available.</p>');
            return;
        }

        var html = '<div class="qsd_history_list">';
        html += '<table class="table table-condensed table-hover" style="margin-bottom:0;">';
        html += '<thead><tr><th>Date</th><th>Author</th><th>Preview</th><th>Actions</th></tr></thead><tbody>';

        for (var i = 0; i < versions.length; i++) {
            var v = versions[i];
            var escapedSnippet = $j('<span>').text(v.snippet).html();
            html += '<tr>';
            html += '<td style="white-space:nowrap;">' + v.date + '</td>';
            html += '<td>' + (v.author || '<em>Unknown</em>') + '</td>';
            html += '<td><small class="qsd_history_snippet">' + escapedSnippet + '</small></td>';
            html += '<td style="white-space:nowrap;">';
            html += '<button type="button" class="btn btn-xs btn-default" '
                  + 'onclick="qsd_preview_version(\'' + edit_id + '\', ' + v.version_id + ')">'
                  + '<span class="glyphicon glyphicon-eye-open"></span> View</button> ';
            html += '<button type="button" class="btn btn-xs btn-warning" '
                  + 'onclick="qsd_restore_version(\'' + qsd_url + '\', \'' + edit_id + '\', ' + v.version_id + ', \'' + v.date.replace(/\\/g, "\\\\").replace(/'/g, "\\'") + '\')">'
                  + '<span class="glyphicon glyphicon-repeat"></span> Restore</button>';
            html += '</td>';
            html += '</tr>';
        }
        html += '</tbody></table></div>';
        $panel.html(html);
    }).fail(function(req) {
        $panel.html('<p style="padding:8px; color:red;">Error loading history: ' + req.responseText + '</p>');
    });
}

function qsd_preview_version(edit_id, version_id)
{
    var $viewDiv = $j("#inline_qsd_" + edit_id);
    // Store original content for "back to current"
    if (!$viewDiv.data('original-content')) {
        $viewDiv.data('original-content', $viewDiv.html());
    }

    $j.get("/admin/ajax_qsd_version_preview", { version_id: version_id }, function(data) {
        $viewDiv.html(
            '<div class="alert alert-warning" style="margin-bottom:8px;">'
            + '<span class="glyphicon glyphicon-time"></span> '
            + 'Viewing historical version. '
            + '<button type="button" class="btn btn-xs btn-default" onclick="qsd_cancel_preview(\'' + edit_id + '\')">'
            + 'Back to current</button>'
            + '</div>'
            + data.content_html
        );
    }).fail(function(req) {
        alert("Error loading version preview: " + req.responseText);
    });
}

function qsd_cancel_preview(edit_id)
{
    var $viewDiv = $j("#inline_qsd_" + edit_id);
    var original = $viewDiv.data('original-content');
    if (original) {
        $viewDiv.html(original);
        $viewDiv.removeData('original-content');
    }
}

function qsd_restore_version(qsd_url, edit_id, version_id, version_date)
{
    if (!confirm('Restore this page to the version from ' + version_date + '?\n\nThis will create a new revision with the old content.')) {
        return;
    }

    refresh_csrf_cookie();
    $j.post("/admin/ajax_qsd_restore", {
        version_id: version_id,
        csrfmiddlewaretoken: csrf_token()
    }, function(data) {
        alert("Version restored successfully. The page will now reload.");
        window.location.reload(true);
    }).fail(function(req) {
        alert("Error restoring version: " + req.responseText);
    });

    $j.post("/varnish/purge_page", {
        page: $j(location).attr('pathname'),
        csrfmiddlewaretoken: csrf_token()
    });
}


