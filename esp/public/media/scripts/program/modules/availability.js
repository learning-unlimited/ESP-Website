var setting = false;
var down = false;

//Records mousedown
function md(td) {
  down = true;
  setting = !isSet(td);
  mo(td);
}

//Enables highlighting multiple cells
function mo(td) {
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