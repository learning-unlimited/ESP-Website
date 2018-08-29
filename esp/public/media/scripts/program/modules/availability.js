function init(isAdmin, disabledClass, disabledText) {
  if (isAdmin) {
    toggle_edit();
  }

  //Sets classes of cells based on status of checkboxes upon loading page
  $j('#checkboxes input:checked').each(function(i, e) {
    if (this.disabled == true) {
      document.getElementsByName($j(this).attr('value'))[0].className = disabledClass;
      document.getElementsByName($j(this).attr('value'))[0].title = disabledText;
    } else {
      document.getElementsByName($j(this).attr('value'))[0].className = "canDo";
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

//Used to keep track of the state of a checkbox
var checkbox_setting = false;
//Used to keep track of whether the mouse is still held down
var mouse_down = false;
//Used to prevent any clicking if on admin page
var noclick = false;

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

function isSet(td) {
  return td.className == "canDo" || td.className == "teaching";
}

//Activate checkbox
function checkbox_on(td) {
  var checkbox = $j('input[value='+td.getAttribute("name")+']')[0]
  if (td.className != "teaching") {
  	td.className = "canDo";
  	checkbox.checked = true;
  }
}

//Deactivate checkbox
function checkbox_off(td) {
  var checkbox = $j('input[value='+td.getAttribute("name")+']')[0]
  if (td.className == "canDo") {
    td.className = "proposed";
    checkbox.checked = false;
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
    }else {
        //prevent availability functions
        noclick = true;
        //prevent clicking other specific fields
        $j(".noclick").css("pointer-events", "none");
        //change button label
        $j("#edit_form").val("Click to Edit Form");
    }
}