$(document).ready(function(){
	var validator=$('#cstform').validate({
		errorPlacement: function(error, element){
			if(element.is(':radio') || element.is(":checkbox"))
				error.appendTo(element.parent().parent().parent().parent());
				
			else error.appendTo(element.parent());
		}
	});
});