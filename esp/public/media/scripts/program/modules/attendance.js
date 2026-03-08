/*
 * Javascript code for the attendance module
*/

var message = '';
var lastResult = '';
Quagga.onDetected(function(result) {
    var code = result.codeResult.code;

    if (lastResult !== code) {
        beep();
        lastResult = code;
        var results = $j("[name=misc_students]")[0];
        var codes = results.value.trim().split(/\s+/).filter(Boolean);
        console.log(codes);
        if (!codes.includes(code)) {
            codes.push(code);
            results.value = codes.join("\n");
            message = code+' added to list';
        } else {
            message = code+' already in list';
        }
        $j('#scaninfo').show();
        $j('#scaninfo').html(message);
        setTimeout("$j('#scaninfo').fadeOut(); ", 4000);
    }
});

prog_url = $j('#attendancescript').data('prog_url');

function update_checkboxes(table) {
    $j(table).find("[name=attending_total]").html($j(table).find("[name=attending]:checked").length);
    $j(table).find("[name=checkedin_total]").html($j(table).find("[name=checkedin]:checked").length);
}

$j(function(){
    function markAttendance(username, secid, undo, callback, errorCallback, undoCheckin){
        refresh_csrf_cookie();
        var data = {student: username, secid: secid, undo: undo, csrfmiddlewaretoken: csrf_token()};
        if (undoCheckin) {
            data.undo_checkin = true;
        }
        $j.post('/teach/' + prog_url + '/ajaxstudentattendance', data, "json").done(callback)
        .fail(errorCallback);
    }

    $j("[name=attending]").on("change", function(){
        var checked = this.checked;
        var $me = $j(this);
        var username = $me.data("username");
        var secid = $me.data("secid");
        var $msg = $me.closest("td").find(".msg");
        var $checkedin = $me.closest("tr").find("[name=checkedin]");
        var $table = $me.closest("table.sortable");
        $me.prop('disabled', true);
        var inFlight = ($table.data('in-flight') || 0) + 1;
        $table.data('in-flight', inFlight);
        $table.addClass('sorttable-busy');
        markAttendance(username, secid, !checked, function(response) {
            if (response.error) {
                alert(response.error);
                $me.prop("checked", !checked);
            } else {
                $me.closest("td").attr("data-st-key", (checked) ? 2 : 1);
                // If this is the webapp, we want to toggle the icons as well
                $me.siblings("i").html(checked ? "check_box" : "check_box_outline_blank");
                if (response.checkedin) {
                    $checkedin.prop("checked", true);
                    $checkedin.closest("td").attr("data-st-key", 2);
                    // If this is the webapp, we want to toggle the icons as well
                    $checkedin.siblings("i").html("check_box");
                }
                // Show undo button after marking attendance
                if (checked) {
                    $msg.find(".undo-attendance").remove();
                    var $undoBtn = $j('<button>')
                        .addClass('btn btn-default btn-mini undo-attendance')
                        .text('Undo')
                        .attr('data-checkedin', response.checkedin ? 'true' : 'false');
                    $undoBtn.on("click", function(e) {
                        e.preventDefault();
                        var undoCheckin = $j(this).attr('data-checkedin') === 'true';
                        $undoBtn.text('Undoing...').prop('disabled', true);
                        markAttendance(username, secid, true, function(resp) {
                            $me.prop("checked", false);
                            $me.closest("td").attr("data-st-key", 1);
                            $me.siblings("i").html("check_box_outline_blank");
                            if (resp.uncheckedin) {
                                $checkedin.prop("checked", false);
                                $checkedin.closest("td").attr("data-st-key", 1);
                                $checkedin.siblings("i").html("check_box_outline_blank");
                            }
                            $msg.text(resp.message);
                            update_checkboxes($table);
                        }, function() {
                            alert("An error occurred while undoing attendance for " + username + ".");
                            $undoBtn.text('Undo').prop('disabled', false);
                        }, undoCheckin);
                    });
                    $msg.html('').append($undoBtn);
                }
                console.log(response.message);
            }
            $me.prop('disabled', false);
            var inFlight = ($table.data('in-flight') || 1) - 1;
            $table.data('in-flight', Math.max(0, inFlight));
            if (inFlight <= 0) {
                $table.removeClass('sorttable-busy');
            }
            update_checkboxes($table);
        }, function(error) {
            alert("An error (" + error.statusText + ") occurred while attempting to update attendance for " + username + ".");
            $me.prop("checked", !checked);
            $msg.text("");
            $me.prop('disabled', false);
            var inFlight = ($table.data('in-flight') || 1) - 1;
            $table.data('in-flight', Math.max(0, inFlight));
            if (inFlight <= 0) {
                $table.removeClass('sorttable-busy');
            }
            // If this is the webapp, we want to toggle the icons as well
            $me.siblings("i").html(!checked ? "check_box" : "check_box_outline_blank");
        });
        $msg.text('Updating attendance...');
    });

    $j("table.sortable").each(function(i, e){
        update_checkboxes(e);
    });
});