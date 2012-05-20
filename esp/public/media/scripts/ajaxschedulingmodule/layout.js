$j(document).ready(function()
{
    // Make the bottom slider div into a jQueryUI slider
    $j("#slider").slider(
	{
	    value: 66,
	    slide: function(event, ui)
	    {
		// Enforce slide limits
		if (ui.value < 15 || ui.value > 85)
		{
		    return false;
		}

		// Set the widths, leaving 2% gap in between
		$j("#matrix-target").css("width", ui.value-1 + "%");
		$j("#directory-target").css("width", 99 - ui.value + "%");
	    },
	});
});
