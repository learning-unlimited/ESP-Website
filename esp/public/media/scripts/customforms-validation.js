$jcf(document).ready(function(){
	var validator=$jcf('#cstform').validate({
		errorPlacement: function(error, element){
			if(element.is(':radio'))
				error.appendTo(element.parent().parent().parent().parent());
			else if(element.is(':checkbox'))
				error.appendTo(element.parent().parent().parent());
				
			else error.appendTo(element.parent());
		}
	});
	
	jQuery.validator.addMethod('USZip', USZipValidator, "Please enter a valid US zip-code");
	jQuery.validator.addMethod('USPhone', USPhoneValidator, "Must be of the format xxx-xxx-xxxx");
	jQuery.validator.addMethod('ddate', DateValidator, "Must be of the format mm/dd/yyyy");
	
	//Initializing the tool-tips
	$jcf('img.qmark').qtip({
		content:{
			text:false
		},
		show:'mouseover',
		hide:'mouseout',
		style: { 
		      padding: 5,
		      background: '#FCEBB6',
		      color: 'black',
		      textAlign: 'left',
			  maxWidth:200,	
			  fontSize:15,	
		      border: {
		         width: 2,
		         radius: 3,
		         color: '#555152'
		      },
		      tip: 'topLeft',
		      name: 'dark' // Inherit the rest of the attributes from the preset dark style
		}
	});
});

var USZipValidator = function(value, element){
	return this.optional(element) || /^\d{5}$/.test(value);
};

var USPhoneValidator = function(value, element){
	return this.optional(element) || /^\d{3}-\d{3}-\d{4}$/.test(value);
};

var DateValidator = function(txtDate, element){
	if(this.optional(element))
		return true;
    var objDate,  // date object initialized from the txtDate string
        mSeconds, // txtDate in milliseconds
        day,      // day
        month,    // month
        year;     // year
    // date length should be 10 characters (no more no less)
    if (txtDate.length !== 10) {
        return false;
    }
    // third and sixth character should be '/'
    if (txtDate.substring(2, 3) !== '/' || txtDate.substring(5, 6) !== '/') {
        return false;
    }
    // extract month, day and year from the txtDate (expected format is mm/dd/yyyy)
    // subtraction will cast variables to integer implicitly (needed
    // for !== comparing)
    month = txtDate.substring(0, 2) - 1; // because months in JS start from 0
    day = txtDate.substring(3, 5) - 0;
    year = txtDate.substring(6, 10) - 0;
    // test year range
    if (year < 1000 || year > 3000) {
        return false;
    }
    // convert txtDate to milliseconds
    mSeconds = (new Date(year, month, day)).getTime();
    // initialize Date() object from calculated milliseconds
    objDate = new Date();
    objDate.setTime(mSeconds);
    // compare input date and parts from Date() object
    // if difference exists then date isn't valid
    if (objDate.getFullYear() !== year ||
        objDate.getMonth() !== month ||
        objDate.getDate() !== day) {
        return false;
    }
    // otherwise return true
    return true;	
};
