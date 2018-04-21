/*
 * Javascript code for the teacher checkin module
*/

$j(function(){
    var input = $j("#shortcuts-box input");
    var selected = 0;
    var checkins = [];

    $j(".flag-detail").hide();

    //Replace hyphens with non-breaking hyphens, to stop Chrome from breaking up phone numbers
    function changeHyphens(n, node){
        node.innerHTML = node.innerHTML.replace(/-/g, "&#8209;");
    }
    $j(".room").map(changeHyphens);
    $j(".phone").map(changeHyphens);

    $j('.section-detail-header').click(function () {
        var info = $j(this).siblings('.section-detail-info');
        var class_id = info.attr('data-class-id');

        // Let data-class-id indicate which class id we want to load details
        // for, as well as whether we still want to load them.
        if (class_id !== '') {

          // Clear the attribute while we're attempting to load details so that
          // we don't try multiple requests for the same class concurrently.
          info.attr('data-class-id', '');

          $j.ajax({
            method: 'GET',
            url: 'ajaxclassdetail',
            data: {
              'class': class_id,
              show_flags: info.attr('data-show-flags'),
            },
            success: function (result) {
              info.html(result);
            },
            error: function (xhr, status, errorThrown) {
              // If an attempt at loading details fails, restore data-class-id
              // so we can try again if the user so requests.
              info.text(errorThrown);
              info.attr('data-class-id', class_id);
            },
          });
        }
        info.toggle('blink');
    });

    function updateSelected(scroll){
        var buttons = $j('.checkin:enabled');
        if(selected >= buttons.length)
            selected = buttons.length-1;
        if(selected < 0)
            selected = 0;
        $j(".selected").removeClass("selected");
        var button = $j(buttons[selected]);
        button.parent().parent().addClass("selected");
        if(scroll){
            if(button.offset().top < $j(document).scrollTop() + window.innerHeight*0.25)
                $j(document).scrollTop(button.offset().top - window.innerHeight*0.25);
            if(button.offset().top > $j(document).scrollTop() + window.innerHeight*0.75)
                $j(document).scrollTop(button.offset().top - window.innerHeight*0.75);
        }
        if(checkins.length>0)
            $j("#last_checkin").html(checkins[checkins.length-1].name).parent().show();
        else
            $j("#last_checkin").parent().hide();
    }
    updateSelected(false);

    function checkIn(username, callback, undo, errorCallback){
        refresh_csrf_cookie();
        var data = {teacher: username, csrfmiddlewaretoken: csrf_token()};
        if(undo)
            data.undo = true;
        $j.post('ajaxteachercheckin', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to " + (undo?"un-check-in ":"check-in ") + username + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
    }

    function undoCheckIn(username, callback, errorCallback){
        checkIn(username, callback, true, errorCallback);
    }

    $j(".checkin:enabled").click(function(){
        var username = this.id.replace("checkin_", "");
        var $me = $j(this);
        var $td = $j(this.parentNode);
        var $msg = $td.children('.message');
        checkIn(username, function(response) {
            $msg.text(response.message);
            $td.prev().prop('class', 'checked-in');
            checkins.push({username: username, name: response.name, $td: $td});
            $me.hide().prop('disabled', true);
            updateSelected(false);

            var $undoButton = $j(document.createElement('button'));
            $undoButton.prop('class', 'btn btn-default btn-mini undo-button');
            $undoButton.text('Undo');
            $undoButton.click(function () {
                undoLiveCheckIn(username);
            });
            $msg.append(' ', $undoButton);
        });
        $msg.text('Checking in...');
    });

    function textTeacher(user, sec, callback, errorCallback){
        var data = {username: user, section: sec, csrfmiddlewaretoken: csrf_token()};
        $j.post('ajaxteachertext', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to text " + user + ".");
            if (errorCallback) {
                errorCallback();
            }
        });
    }

    $j(".text").click(function(){
        var username = $j(this).data("username");
        var section = $j(this).data("section");
        var $td = $j(this.parentNode);
        var $msg = $td.children('.message');
        textTeacher(username, section, function(response) {
            $msg.text(response.message);
        });
        $j(this).attr("disabled",true);
        $msg.text('Texting teacher...');
    });

    $j(".uncheckin:enabled").click(function(){
        var username = this.id.replace("uncheckin_", "");
        undoCheckIn(username, function(response) {
            alert(response.message);
            location.reload();
        });
        this.value += "...";
    });

    // Undo the check in of the user with the specified username, assuming
    // that that user was not checked in when this page was loaded (because
    // the DOM would look different depending on whether that were true). If
    // no username specified, undo the last check in.
    function undoLiveCheckIn(username) {
        var targetCheckin;
        if (username === undefined) {
            if (checkins.length === 0) {
                return false;
            }
            targetCheckin = checkins[checkins.length - 1];
        } else {
            // search from the back because we assume more recent checkins
            // are more likely to be undone
            // (TODO if undoing changes from long ago is actually used a lot:
            // make this a hash)
            for (var i = checkins.length - 1; i >= 0; i--) {
                if (checkins[i].username === username) {
                    targetCheckin = checkins[i];
                    break;
                }
            }
        }
        if (targetCheckin === undefined) {
            alert("No check-in for " + username + " found to undo");
            return;
        }
        username = targetCheckin.username;
        var $td = targetCheckin.$td;
        var $msg = $td.children('.message');
        var $undoButton = $msg.children('.undo-button');
        $undoButton.text('Undoing...').prop('disabled', true);
        undoCheckIn(username, function(response) {
            // find targetCheckin in checkins and splice it out
            for (var i = checkins.length - 1; i >= 0; i--) {
                if (checkins[i] === targetCheckin) {
                    checkins.splice(i, 1);
                    break;
                }
            }
            $msg.html(response.message+"<br/>");
            $td.children('.checkin').show().prop('disabled', false);
            $td.prev().prop('class', 'not-checked-in');
            selected = $j('.checkin:enabled').index($td.find('.checkin'));
            updateSelected(true);
        }, function() {
            // on error, re-enable undo so you can try again
            $undoButton.text('Undo').prop('disabled', false);
        });
    }

    $j(document).keypress(function(e){
        if(e.which==13 && e.shiftKey){
            $j(".selected .checkin").click();
            e.preventDefault();
            input.val("");
        }
        else if((e.which==122 || e.which==26) && e.ctrlKey){
            undoLiveCheckIn();
            e.preventDefault();
        }
        else if(e.which==63){
            window.open($j(".selected a")[0].href);
            e.preventDefault();
        }
    }).keydown(function(e){
        if(e.target.nodeName !== "TEXTAREA" && e.target.nodeName !== "INPUT") {
            input.focus();
            if(e.which==38)
                selected--;
            else if(e.which==40)
                selected++;
            else if(e.which==33)
                selected-=5;
            else if(e.which==34)
                selected+=5;
            else
                return;
            updateSelected(true);
            e.preventDefault();
        }
    }).keyup(function(e){
        input.change();
    });

    var lastLength=0;
    input.change(function(e){
        if(input.val().length == 0)
            input.removeClass();
        else if(input.val().length > lastLength || input.hasClass("not-found")){
            var found=false;
            var buttons = $j(".checkin");
            for(var n=0; !found && n<buttons.length; n++)
                if(buttons[n].name.toLowerCase().indexOf(input.val().toLowerCase())==0){
                    selected=n;
                    found=true;
                }
            for(var n=0; !found && n<buttons.length; n++)
                if($j(buttons[n]).parent().prev().children("a").html().toLowerCase().indexOf(input.val().toLowerCase())==0){
                    selected=n;
                    found=true;
                }
            if(found)
                updateSelected(true);
            input.removeClass().addClass(found?"found":"not-found");
        }
        lastLength = input.val().length;
    });
});
