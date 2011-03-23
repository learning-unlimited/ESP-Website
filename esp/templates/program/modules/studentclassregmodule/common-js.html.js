// Common JS

function submit_prereg(clsid) {
   // prereg for a class
   document.getElementById('submitbutton'+clsid).setAttribute("class", "addbutton_disabled");
   return true;
}

function submit_override_prereg(clsid) {
   // prereg for a class
   if (confirm('Are you sure you want to override this block?') &&
       confirm('Are you really sure?!?')) {
      document.getElementById('submitbutton'+clsid).disabled = true;
      return true;
   }
   return false;
}

function swap_visible(div_id) {
	var div = document.getElementById(div_id);
	if (div.style.display == 'none') {
		div.style.display = '';
	} else {
		div.style.display = 'none';
	}
}

