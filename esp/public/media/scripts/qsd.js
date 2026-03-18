
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
            var escapedDate = $j('<span>').text(v.date).html();
            var escapedAuthor = v.author ? $j('<span>').text(v.author).html() : '<em>Unknown</em>';
            html += '<tr>';
            html += '<td style="white-space:nowrap;">' + escapedDate + '</td>';
            html += '<td>' + escapedAuthor + '</td>';
            html += '<td><small class="qsd_history_snippet">' + escapedSnippet + '</small></td>';
            html += '<td style="white-space:nowrap;">';
            html += '<button type="button" class="btn btn-xs btn-default qsd-view-btn" '
                  + 'data-qsd-url="' + qsd_url + '" data-edit-id="' + edit_id + '" '
                  + 'data-version-id="' + v.version_id + '" data-version-date="' + escapedDate + '">'
                  + '<span class="glyphicon glyphicon-eye-open"></span> View</button> ';
            html += '<button type="button" class="btn btn-xs btn-warning qsd-restore-btn" '
                  + 'data-qsd-url="' + qsd_url + '" data-edit-id="' + edit_id + '" '
                  + 'data-version-id="' + v.version_id + '" data-version-date="' + escapedDate + '">'
                  + '<span class="glyphicon glyphicon-repeat"></span> Restore</button>';
            html += '</td>';
            html += '</tr>';
        }
        html += '</tbody></table></div>';
        $panel.html(html);

        // Delegated event handlers (avoids inline onclick escaping issues)
        // Use .off() first to prevent duplicate bindings on repeated toggle
        $panel.off('click', '.qsd-view-btn').on('click', '.qsd-view-btn', function() {
            var $btn = $j(this);
            qsd_preview_version($btn.data('qsd-url'), $btn.data('edit-id'),
                                $btn.data('version-id'), $btn.data('version-date'));
        });
        $panel.off('click', '.qsd-restore-btn').on('click', '.qsd-restore-btn', function() {
            var $btn = $j(this);
            qsd_restore_version($btn.data('qsd-url'), $btn.data('edit-id'),
                                $btn.data('version-id'), $btn.data('version-date'));
        });
    }).fail(function(req) {
        $panel.empty().append(
            $j('<p style="padding:8px; color:red;"></p>').text('Error loading history: ' + req.responseText)
        );
    });
}

function qsd_preview_version(qsd_url, edit_id, version_id, version_date)
{
    var $viewDiv = $j("#inline_qsd_" + edit_id);
    var $editDiv = $j("#inline_edit_" + edit_id);

    // Store original content for "back to current"
    if (!$viewDiv.data('original-content')) {
        $viewDiv.data('original-content', $viewDiv.html());
    }

    // Track which version was last viewed (for highlighting after cancel)
    var $panel = $j("#qsd_history_panel_" + edit_id);
    $panel.data('last-viewed-version', version_id);

    $j.get("/admin/ajax_qsd_version_preview", { version_id: version_id }, function(data) {
        $viewDiv.html(
            '<div class="alert alert-warning" style="margin-bottom:8px;">'
            + '<span class="glyphicon glyphicon-time"></span> '
            + 'Viewing historical version. '
            + '<button type="button" class="btn btn-xs btn-default qsd-back-to-current-btn">'
            + '<span class="glyphicon glyphicon-arrow-left"></span> Back to current</button> '
            + '<button type="button" class="btn btn-xs btn-warning qsd-preview-restore-btn">'
            + '<span class="glyphicon glyphicon-repeat"></span> Restore this version</button>'
            + '</div>'
            + data.content_html
        );
        // Bind buttons via jQuery (avoids inline onclick escaping issues)
        $viewDiv.find('.qsd-back-to-current-btn').on('click', function() {
            qsd_cancel_preview(edit_id);
        });
        $viewDiv.find('.qsd-preview-restore-btn').on('click', function() {
            qsd_restore_version(qsd_url, edit_id, version_id, version_date);
        });
        // Show the view div (hidden during inline editing) and hide the editor
        $viewDiv.removeClass('hidden').addClass('qsd_view_visible');
        if ($editDiv.length) {
            $editDiv.addClass('hidden').removeClass('qsd_edit_visible');
        }
    }).fail(function(req) {
        alert("Error loading version preview: " + req.responseText);
    });
}

function qsd_cancel_preview(edit_id)
{
    var $viewDiv = $j("#inline_qsd_" + edit_id);
    var $editDiv = $j("#inline_edit_" + edit_id);
    var original = $viewDiv.data('original-content');
    if (original) {
        $viewDiv.html(original);
        $viewDiv.removeData('original-content');
    }
    // Restore inline edit mode: hide view div, show editor
    if ($editDiv.length) {
        $viewDiv.removeClass('qsd_view_visible').addClass('hidden');
        $editDiv.removeClass('hidden').addClass('qsd_edit_visible');
    }
    // Highlight the last-viewed version's View button in the history panel
    var $panel = $j("#qsd_history_panel_" + edit_id);
    var lastViewed = $panel.data('last-viewed-version');
    if (lastViewed) {
        $panel.find('.qsd-view-btn').removeClass('qsd-last-viewed');
        $panel.find('.qsd-last-viewed-label').remove();
        var $btn = $panel.find('.qsd-view-btn[data-version-id="' + lastViewed + '"]');
        $btn.addClass('qsd-last-viewed');
        $btn.after('<span class="qsd-last-viewed-label"> ← last viewed</span>');
    }
}

function qsd_restore_version(qsd_url, edit_id, version_id, version_date)
{
    // Remove any existing modal
    $j("#qsd-restore-modal").remove();

    var modalHtml =
        '<div class="modal hide fade" id="qsd-restore-modal" tabindex="-1" role="dialog">'
      + '  <div class="modal-header">'
      + '    <button type="button" class="close" data-dismiss="modal">&times;</button>'
      + '    <h4><span class="glyphicon glyphicon-repeat"></span> Restore Version</h4>'
      + '  </div>'
      + '  <div class="modal-body">'
      + '    <p>Restore this page to the version from <strong>' + $j('<span>').text(version_date).html() + '</strong>?</p>'
      + '    <p class="muted">This will create a new revision with the old content.</p>'
      + '  </div>'
      + '  <div class="modal-footer">'
      + '    <button type="button" class="btn" data-dismiss="modal">Cancel</button>'
      + '    <button type="button" class="btn btn-warning" id="qsd-restore-confirm-btn">'
      + '      <span class="glyphicon glyphicon-repeat"></span> Restore'
      + '    </button>'
      + '  </div>'
      + '</div>';

    $j("body").append(modalHtml);
    var $modal = $j("#qsd-restore-modal");
    $modal.modal("show");

    $j("#qsd-restore-confirm-btn").on("click", function() {
        var $btn = $j(this);
        $btn.prop("disabled", true).html('<span class="glyphicon glyphicon-refresh"></span> Restoring...');

        refresh_csrf_cookie();
        $j.post("/admin/ajax_qsd_restore", {
            version_id: version_id,
            csrfmiddlewaretoken: csrf_token()
        }, function(data) {
            $modal.find(".modal-body").html(
                '<div class="alert alert-success" style="margin-bottom:0;">'
              + '<span class="glyphicon glyphicon-ok"></span> Version restored successfully. Reloading page...'
              + '</div>'
            );
            $modal.find(".modal-footer").remove();
            setTimeout(function() { window.location.reload(true); }, 1000);
        }).fail(function(req) {
            $btn.prop("disabled", false).html('<span class="glyphicon glyphicon-repeat"></span> Restore');
            $modal.find(".modal-body").append(
                '<div class="alert alert-danger" style="margin-top:10px;">'
              + '<span class="glyphicon glyphicon-exclamation-sign"></span> Error: ' + $j('<span>').text(req.responseText).html()
              + '</div>'
            );
        });
    });

    // Cleanup on close (Bootstrap 2 uses "hidden" event without namespace)
    $modal.on("hidden", function() { $j(this).remove(); });
}


