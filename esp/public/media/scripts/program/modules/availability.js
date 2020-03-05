/*
This code provides a way to have an availability or signup page with whenisgood.net-like behavior. This includes clicking single cells to switch their status, but also holding down and moving the mouse to multiple cells to switch all of their statuses to on or off (depending on the status of the cell that was originally clicked). Users can also click a <th> to switch the status of an entire table column.
A generic version of this is implemented in templates/program/modules/availability.html, so any other implementation should be modelled off of that.
This has been designed to create an interface between the cells of the table and (hidden) checkboxes within a form on the page. The checkboxes should be within a div with the id "checkboxes" and each checkbox should follow the following guidelines:
- the checkbox should correspond to a single <td> element on the page (and vice versa)
- the checkbox should have a value that matches the name of the respective <td> (and vice-versa)
- the checkbox should have the checked attribute if the checkbox is "on" and the respective <td> should reflect this
- the checkbox should have the disabled attribute if you do not want the user to change the status of the <td> (and thus the checkbox)
- the checkbox should have the data-hover attribute with custom text if you'd like that text to be displayed when hovering over the respective <td>
This should leave plenty of flexibility for the use of the id and name attributes of the checkboxes to maintain form functionality.
*/

var Availability = (function () {
    //Used to keep track of the state of a checkbox
    var checkbox_setting = false;
    //Used to keep track of whether the mouse is still held down
    var mouse_down = false;
    //Used to prevent any clicking if on admin page
    var noclick = false;
    
    function isSet(td) {
        return $j(td).hasClass("canDo");
    }
    
    //Activate checkbox
    function checkbox_on(td) {
        var checkbox = $j('input[value='+td.getAttribute("name")+']')[0]
        $j(td).removeClass("proposed");
        $j(td).addClass("canDo");
        checkbox.checked = true;
        checkbox.disabled = false;
    }

    //Deactivate checkbox
    function checkbox_off(td) {
        var checkbox = $j('input[value='+td.getAttribute("name")+']')[0]
        if (!$j(td).hasClass("teaching") && $j(td).hasClass("canDo")) {
            $j(td).removeClass("canDo");
            $j(td).addClass("proposed");
            checkbox.checked = false;
        }
    }
    
    //Records mouseup
    function mouseup_event() {
        mouse_down=false;
    }
    
    //Records mousedown
    function mousedown_event(td) {
        if (noclick) return;
        mouse_down = true;
        checkbox_setting = !isSet(td);
        mouseover_event(td);
    }

    //Enables highlighting multiple cells
    function mouseover_event(td) {
        if (noclick) return;
        if (!mouse_down) return;
        if (checkbox_setting) {
            checkbox_on(td);
        } else {
            checkbox_off(td);
        }
    }

    //Clicking the header turns the entire block on/off
    function header_switch(e, col) {
        if (noclick) return;
        var somethingToSet = false;
        var block = document.getElementById("block_" + col);
        for (var i = 1; i < block.rows.length; i++) {
            var td = block.rows[i].cells[0];
            if (!isSet(td)) somethingToSet = true;
        }
        for (var i = 1; i < block.rows.length; i++) {
            var td = block.rows[i].cells[0];
            if (somethingToSet) {
                checkbox_on(td);
            } else {
                checkbox_off(td);
            }
        }
    }

    function toggle_edit() {
        if (noclick){
            //allow availability functions
            noclick = false;
            //allow clicking other specific fields
            $j(".noclick").css("pointer-events", "auto");
            //change button label
            $j("#edit_form").val("Click to Stop Editing Form");
        } else {
            //prevent availability functions
            noclick = true;
            //prevent clicking other specific fields
            $j(".noclick").css("pointer-events", "none");
            //change button label
            $j("#edit_form").val("Click to Edit Form");
        }
    }
    
    function init(isAdmin, disabledText) {
        if (isAdmin) {
            toggle_edit();
        }

        //Sets classes of cells based on status of checkboxes upon loading page
        $j('#checkboxes input').each(function(i, e) {
            var cell = document.getElementsByName($j(this).attr('value'))[0]
            if (this.disabled == true) {
                $j(cell).removeClass("proposed");
                $j(cell).addClass("teaching");
                cell.title = disabledText;
            }
            if (this.checked == true) {
                $j(cell).removeClass("proposed");
                $j(cell).addClass("canDo");
            }
        });

        //Populate the right sidebar
        $j(document).ready(function () {
            $j(".wrap").append($j(".right"));
            $j(".right").show();
        });

        //If there is hover text, show it when hovering over the timeslot
        $j(".group td").mouseover(function() {
            var hover_text = $j('input[value='+parseInt($j(this).attr('name'))+']').data('hover')
            if (hover_text) {
                $j(".left .summary").html(hover_text);
                $j(".left .summary").css("display", "block");
            }
        }).mouseout(function() {
            $j(".left .summary").css("display", "none");
        });
    }

    return {
        mouseup_event: mouseup_event,
        mousedown_event: mousedown_event,
        mouseover_event: mouseover_event,
        header_switch: header_switch,
        toggle_edit: toggle_edit,
        init: init
    };
})();