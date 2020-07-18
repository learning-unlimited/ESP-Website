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
        var results = document.querySelector('textarea');
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

$j(function(){
    function markAttendance(username, section, callback, undo, errorCallback){
        refresh_csrf_cookie();
        var data = {student: username, section: section, csrfmiddlewaretoken: csrf_token()};
        if(undo)
            data.undo = true;
        $j.post('/teach/' + prog_url + '/ajaxstudentattendance', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to " + (undo?"un-check-in ":"check-in ") + username + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
    }

    function undoAttendance(username, section, callback, errorCallback){
        markAttendance(username, section, callback, true, errorCallback);
    }

    $j(".checkin:enabled").click(function(){
        var username = this.id.replace("checkin_", "");
        var $me = $j(this);
        var section = $me.data("section");
        var $td = $j(this.parentNode);
        var $msg = $td.children('.message');
        var $txtbtn = $j(this).closest('tr').find('.text');
        markAttendance(username, section, function(response) {
            // $msg.text(response.message);
            // $td.prev().prop('class', 'checked-in');
            // checkins.push({username: username, name: response.name, $td: $td});
            $me.hide().prop('disabled', true);
            // $txtbtn.prop('disabled', true);
            // $txtbtn.attr("title","Teacher already checked-in");
            // updateSelected(false);

            // var $undoButton = $j(document.createElement('button'));
            // $undoButton.prop('class', 'btn btn-default btn-mini undo-button');
            // $undoButton.text('Undo');
            // $undoButton.click(function () {
                // undoLiveCheckIn(username);
            // });
            // $msg.append(' ', $undoButton);
        });
        $msg.text('Checking in...');
    });

    // $j(".uncheckin:enabled").click(function(){
        // var username = this.id.replace("uncheckin_", "");
        // var section = $j(this).data("section");
        // undoAttendance(username, section, function(response) {
            // alert(response.message);
            // location.reload();
        // });
        // this.value += "...";
    // });
});