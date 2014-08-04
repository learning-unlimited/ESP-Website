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
    
    function updateSelected(scroll){
        var buttons = $j(".checkin");
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
    
    function checkIn(username, callback, undo){
        refresh_csrf_cookie();
        var data = {teacher: username, csrfmiddlewaretoken: csrf_token()};
        if(undo)
            data.undo = true;
        $j.post('ajaxteachercheckin', data, "json").success(callback)
        .error(function(){
            alert("An error occurred while atempting to " + (undo?"un-check-in ":"check-in ") + username + ".");
        });
    }
    
    function undoCheckIn(username, callback){
        checkIn(username, callback, true);
    }
    
    $j(".checkin:enabled").click(function(){
        var username = this.id.replace("checkin_", "");
        var td = this.parentNode;
        var oldTd = $j(td).clone(true)[0];
        checkIn(username, function(response) {
            td.innerHTML = response.message;
            td.previousElementSibling.className = "checked-in";
            checkins.push({username: username, name: response.name, td: td, oldTd: oldTd});
            updateSelected(false);
        });
        this.value += "...";
    });
    
    $j(".uncheckin:enabled").click(function(){
        var username = this.id.replace("uncheckin_", "");
        undoCheckIn(username, function(response) {
            alert(response.message);
            location.reload();
        });
        this.value += "...";
    });

    $j(document).keypress(function(e){
        if(e.which==13 && e.shiftKey){
            $j(".selected .checkin").click();
            e.preventDefault();
            input.val("");
        }
        else if((e.which==122 || e.which==26) && e.ctrlKey){
            if(checkins.length>0){
                var lastCheckin = checkins[checkins.length - 1];
                var username = lastCheckin.username;
                var td = lastCheckin.td;
                var oldTd = lastCheckin.oldTd;
                undoCheckIn(username, function(response) {
                    if(checkins[checkins.length - 1] === lastCheckin)
                        checkins.pop();
                    $j(td).replaceWith($j(oldTd).prepend(response.message+"<br/>"));
                    oldTd.previousElementSibling.className = "not-checked-in";
                    selected = $j(".checkin").index($j(oldTd).find("input"));
                    updateSelected(true);
                });
                td.innerHTML += " Undo...";
            }
            e.preventDefault();
        }
        else if(e.which==63){
            window.open($j(".selected a")[0].href);
            e.preventDefault();
        }
    }).keydown(function(e){
        if(e.target.nodeName !== "TEXTAREA") {
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
