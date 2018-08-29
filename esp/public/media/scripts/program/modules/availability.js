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

var setting = false;
var down = false;
var noclick = false;

//Records mousedown
function md(td) {
  if (noclick) return;
  down = true;
  setting = !isSet(td);
  mo(td);
}

//Enables highlighting multiple cells
function mo(td) {
  if (noclick) return;
  if (!down) return;
  if (setting) {
    on(td);
  } else {
    off(td);
  }
}

function isSet(td) {
  return td.className == "canDo" || td.className == "teaching";
}

//Activate checkbox
function on(td) {
  var checkbox = $j('input[value='+td.getAttribute("name")+']')[0]
  if (td.className != "teaching") {
  	td.className = "canDo";
  	checkbox.checked = true;
  }
}

//Deactivate checkbox
function off(td) {
  var checkbox = $j('input[value='+td.getAttribute("name")+']')[0]
  if (td.className == "canDo") {
    td.className = "proposed";
    checkbox.checked = false;
  }
}

//Clicking the header turns the entire block on/off
function header(e, col) {
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
      on(td);
    } else {
      off(td);
    }
  }
}

//Populate the right sidebar
$j(document).ready(function () {
  $j(".wrap").append($j(".right"));
  $j(".right").show();
});

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