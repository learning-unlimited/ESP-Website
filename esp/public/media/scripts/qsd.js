
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

    // Clear out any conflict banner left over from a previous failed save.
    var msgBox = document.getElementById("inline_conflict_" + edit_id);
    if (msgBox) {
        msgBox.className = "hidden";
        msgBox.textContent = "";
    }

    // Collapse the version-history panel back down -- it should only be
    // open when the user just clicked "History", not left over from an
    // earlier edit session on this same page load.
    var historyPanel = document.getElementById("inline_history_" + edit_id);
    if (historyPanel) {
        historyPanel.className = "qsd_bits hidden";
    }
    var loadedMsg = document.getElementById("inline_history_loaded_" + edit_id);
    if (loadedMsg) {
        loadedMsg.textContent = "";
    }

    // Warn if this block's starting point (baked into whatever page last
    // rendered it, which may itself be a stale/cached render) is already
    // out of date, rather than only finding out when trying to save.
    var container = document.getElementById("inline_edit_" + edit_id);
    qsd_warn_if_stale(qsd_url, container.getAttribute("data-orig-id"),
        container.getAttribute("data-orig-version"), "qsd_content_" + edit_id);
}

function qsd_warn_if_stale(qsd_url, orig_id, orig_version, textarea_id)
{
    // Shared by the inline editor (on opening a block) and the full-page
    // editor (on page load): warns if this editor's starting point is
    // already out of date, before the user invests time typing.
    refresh_csrf_cookie();
    $j.post("/admin/ajax_qsd", post_encode({
        cmd: "check_fresh",
        url: qsd_url,
        orig_id: orig_id,
        orig_version: orig_version,
        csrfmiddlewaretoken: csrf_token()
    }), function(data, status) {
        if (status === "success" && data) {
            var result = JSON.parse(data);
            // Also treat a mismatch between the actual current content and
            // what's sitting in the textarea as "stale", even if the
            // orig_id/orig_version tokens themselves look fresh -- catches
            // a browser silently restoring a stale <textarea> value across
            // a plain page refresh (a browser form-state quirk that
            // check_freshness's token comparison alone can't see, since
            // orig_id/orig_version are plain div/hidden-input attributes,
            // not something the browser tries to "helpfully" restore the
            // same way).
            //
            // Normalize line endings before comparing: per the HTML spec, a
            // <textarea>'s .value is normalized to LF-only, but content
            // saved with CRLF line endings (e.g. legacy/imported content)
            // stays CRLF in the database and in this AJAX response. Without
            // this, that mismatch alone would trip a false "stale" alert on
            // every load of such content, including immediately after
            // saving it -- nothing was actually stale.
            var textarea = document.getElementById(textarea_id);
            var normalizeLineEndings = function(s) { return s.replace(/\r\n/g, '\n'); };
            var contentMismatch = textarea && result.content !== undefined
                && normalizeLineEndings(textarea.value) !== normalizeLineEndings(result.content);
            if (result.stale || contentMismatch) {
                alert("Heads up: this content has changed since this page was loaded. " +
                      "Please hard-refresh the page (Ctrl+Shift+R, or Cmd+Shift+R on Mac) " +
                      "before editing, to avoid a conflict when you save.");
            }
        }
    });
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
        if (request.status === 409) {
            // Conflict: refresh this block's orig_id/orig_version to the
            // current state, so that clicking "Save changes" again is a
            // deliberate override rather than resubmitting the same stale
            // tokens and hitting the same conflict again.
            try {
                var payload = JSON.parse(request.responseText);
                var container = document.getElementById("inline_edit_" + edit_id);
                if (container) {
                    container.setAttribute("data-orig-id", payload.orig_id);
                    container.setAttribute("data-orig-version", payload.orig_version);
                }
                // Shown as an in-page red banner (matching the full-page
                // editor's conflict banner) rather than a popup alert.
                var msgBox = document.getElementById("inline_conflict_" + edit_id);
                if (msgBox) {
                    msgBox.textContent = payload.message;
                    msgBox.className = "alert alert-danger";
                }
                return;
            } catch (e) {
                // Fall through to the generic handling below.
            }
        }
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
    if (action === 'save') {
        // Stay in the edit view until we know the save actually succeeded --
        // on success the page reloads anyway (see qsd_send_command), and on
        // failure/conflict the user's unsaved edit and the error message
        // should stay visible instead of disappearing behind the read view.
        var container = document.getElementById("inline_edit_" + edit_id);
        var content = document.getElementById("qsd_content_" + edit_id).value;
        var postdata = {
            cmd: "update",
            url: qsd_url,
            data: content,
            orig_id: container.getAttribute("data-orig-id"),
            orig_version: container.getAttribute("data-orig-version")
        };
        qsd_send_command(qsd_url, edit_id, postdata);
        return;
    }

    //  Switch the visibility of the edit and view areas.
    document.getElementById("inline_edit_" + edit_id).className = "hidden";
    $j("#inline_edit_msg_" + edit_id).show();
    document.getElementById("inline_qsd_" + edit_id).className = "qsd_view_visible";

    if (action) {
        var content = document.getElementById("qsd_content_" + edit_id).value;
        qsd_send_preview(qsd_url, edit_id, {data: content});
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

function qsd_inline_history(qsd_url, edit_id)
{
    var panel = document.getElementById("inline_history_" + edit_id);

    // Toggle: if already open, just close it.
    if (panel.className.indexOf("hidden") === -1) {
        panel.className = "qsd_bits hidden";
        return;
    }

    refresh_csrf_cookie();
    $j.post("/admin/ajax_qsd", post_encode({
        cmd: "history",
        url: qsd_url,
        csrfmiddlewaretoken: csrf_token()
    }), function(data, status) {
        if (status !== "success" || !data) return;
        var result = JSON.parse(data);
        var select = document.getElementById("inline_history_select_" + edit_id);
        select.innerHTML = "";
        result.history.forEach(function(h, i) {
            var opt = document.createElement("option");
            opt.value = h.version_id;
            opt.text = h.user + " -- " + h.date + (i === 0 ? " (current)" : "");
            select.appendChild(opt);
        });
        // What you'd see if this block were disabled or had never been
        // saved -- not itself a saved version, so it's appended after the
        // real history rather than mixed into it.
        var defaultOpt = document.createElement("option");
        defaultOpt.value = "__default__";
        defaultOpt.text = "(default content for this block)";
        select.appendChild(defaultOpt);
        var loadedMsg = document.getElementById("inline_history_loaded_" + edit_id);
        if (loadedMsg) { loadedMsg.textContent = ""; }
        panel.className = "qsd_bits";
    }).fail(function(request, jquery_status, http_status) {
        alert(jquery_status + ": " + http_status + "\n" + request.responseText);
    });
}

function qsd_inline_load_into_editor(edit_id, content, message)
{
    // Shared by both the "load a past version" and "load the default
    // content" paths: writes the raw content into the editable textarea
    // and syncs the rich-text/markdown widget bound to it, if any, rather
    // than showing it in a separate read-only box. The user can review it
    // in the same box they'd normally type in -- toggle to HTML source
    // view, edit it further, etc -- then just click the existing "Save
    // changes" button to keep it (a normal, fully conflict-checked save)
    // or "Cancel" to discard it.
    var textarea = document.getElementById("qsd_content_" + edit_id);
    textarea.value = content;
    var setter = window.qsd_editor_setters && window.qsd_editor_setters[edit_id];
    if (setter) { setter(content); }

    var loadedMsg = document.getElementById("inline_history_loaded_" + edit_id);
    if (loadedMsg) { loadedMsg.textContent = message; }
}

function qsd_inline_preview_version(qsd_url, edit_id)
{
    var select = document.getElementById("inline_history_select_" + edit_id);
    var version_id = select.value;
    if (!version_id) return;

    if (version_id === "__default__") {
        // No DB round-trip needed -- the default content was already
        // rendered into the page (see qsd_default_content_<id>).
        var defaultEl = document.getElementById("qsd_default_content_" + edit_id);
        qsd_inline_load_into_editor(edit_id, defaultEl ? defaultEl.value : "",
            "Loaded the default content for this block into the editor below — not saved yet.");
        return;
    }

    refresh_csrf_cookie();
    $j.post("/admin/ajax_qsd", post_encode({
        cmd: "preview_version",
        url: qsd_url,
        version_id: version_id,
        csrfmiddlewaretoken: csrf_token()
    }), function(data, status) {
        if (status !== "success" || !data) return;
        var result = JSON.parse(data);
        qsd_inline_load_into_editor(edit_id, result.content,
            "Loaded version from " + result.date + " by " + result.user +
            " into the editor below — not saved yet.");
    }).fail(function(request, jquery_status, http_status) {
        alert(jquery_status + ": " + http_status + "\n" + request.responseText);
    });
}


