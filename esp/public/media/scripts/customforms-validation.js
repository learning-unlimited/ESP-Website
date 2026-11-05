/* Lightweight jQuery.browser polyfill for qTip compatibility */
(function($){
	if (!$.browser) {
		var ua = (navigator.userAgent || '').toLowerCase();
		$.browser = {
			msie: /(msie|trident)/.test(ua),
			version: (ua.match(/(?:msie |rv:)(\d+(?:\.\d+)?)/) || [])[1] || ''
		};
	}
})(jQuery);

$j(function(){
	$j('#cstform').validate({
		errorPlacement: function(error, element){
			if (element.is(':radio')) {
				error.appendTo(element.parent().parent().parent().parent());
			} else if (element.is(':checkbox')) {
				error.appendTo(element.parent().parent().parent());
			} else {
				error.appendTo(element.parent());
			}
		}
	});

	$j.validator.addMethod('USZip', USZipValidator, "Please enter a valid US zip-code");
	$j.validator.addMethod('ddate', DateValidator, "Please enter a valid date, e.g. 11/14/2026");

	// Initializing the tool-tips
	$j('img.qmark').qtip({
		content: { text: false },
		show: 'mouseover',
		hide: 'mouseout',
		style: {
			padding: 5,
			background: '#FCEBB6',
			color: 'black',
			textAlign: 'left',
			maxWidth: 200,
			fontSize: 15,
			border: {
				width: 2,
				radius: 3,
				color: '#555152'
			},
			tip: 'topLeft',
			name: 'dark'
		}
	});
});

function USZipValidator(value, element){
	return this.optional(element) || /^\d{5}$/.test(value);
}

// Accepts mm/dd/yyyy, and yyyy-mm-dd, which is how saved dates are re-displayed.
function DateValidator(txtDate, element){
	if (this.optional(element)) return true;
	let objDate, mSeconds, day, month, year;

	if (/^\d{4}-\d{2}-\d{2}$/.test(txtDate)) {
		year = txtDate.substring(0, 4) - 0;
		month = txtDate.substring(5, 7) - 1;
		day = txtDate.substring(8, 10) - 0;
	} else if (/^\d{2}\/\d{2}\/\d{4}$/.test(txtDate)) {
		month = txtDate.substring(0, 2) - 1;
		day = txtDate.substring(3, 5) - 0;
		year = txtDate.substring(6, 10) - 0;
	} else {
		return false;
	}

	if (year < 1000 || year > 3000) return false;

	mSeconds = (new Date(year, month, day)).getTime();
	objDate = new Date();
	objDate.setTime(mSeconds);

	if (objDate.getFullYear() !== year || objDate.getMonth() !== month || objDate.getDate() !== day) return false;
	return true;
}
