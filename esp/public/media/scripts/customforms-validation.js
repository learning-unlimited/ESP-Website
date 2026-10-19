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
	$j.validator.addMethod('USPhone', USPhoneValidator, "Please enter a 10-digit phone number, e.g. 617-555-0101");
	$j.validator.addMethod('ddate', DateValidator, "Must be of the format mm/dd/yyyy");

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

// Also accepts the formats the phone widget re-displays, e.g. "(617) 555-0101".
function USPhoneValidator(value, element){
	return this.optional(element) || /^(\+?1[\s.-]?)?(\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}$/.test(value);
}

// Accepts mm/dd/yyyy, and yyyy-mm-dd, which is how saved dates are re-displayed.
function DateValidator(txtDate, element){
	if (this.optional(element)) return true;
	let objDate, mSeconds, day, month, year;

	if (txtDate.length !== 10) return false;
	if (txtDate.substring(4, 5) === '-' && txtDate.substring(7, 8) === '-') {
		year = txtDate.substring(0, 4) - 0;
		month = txtDate.substring(5, 7) - 1;
		day = txtDate.substring(8, 10) - 0;
	} else if (txtDate.substring(2, 3) === '/' && txtDate.substring(5, 6) === '/') {
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
