function check_grade_range(form, grade_min, grade_max)
{
    console.log("Checking!");
// Local changes (chapter request) made by milescalabresi... apparently
// one can't use template overrides to tweak scripts like this one.

//    if ($j(form).find('#id_grade_min').val() == grade_min && $j(form).find('#id_grade_max').val() == grade_max)
//    {
//        return confirm("Are you sure you want your class to have grade range "+grade_min+"-"+grade_max+"? \
//Managing a class with grade range "+grade_min+"-"+grade_max+" can be more difficult due to the \
//difference in maturity levels between middle and high school students. \
//Click OK if you are sure this is what you want, or click Cancel to go back \
//and change the grade range.");
//    }
    if ($j(form).find('#id_grade_min').val() > 8)
    {
        return confirm("Hey there! We really need some classes open to middle"
                       +" school students. Would you consider helping us out by"
                       +" opening your class to them? Click Cancel to go back"
                       +" and change your minimum grade, or click OK to"
                       +" proceed with your original selection. Thanks for"
                       +" your consideration :) and if you hit OK but still"
		       +" can't submit, check your ad-blocker or other add-ons."
		       +" (If you still can't submit after that, email us at"
		       +" yalesplash@gmail.com and we'll help you sort it out.");
    }  else
    {
        return true;
    }
}

function setup_autocomplete()
{
    $j("#teacher_name").autocomplete({
	source: function(request, response) {
            $j.ajax({
		url: "/teach/"+base_url+"/teacherlookup/",
		dataType: "json",
		data: {name: request.term},
		success: function(data) {
		    var output = $j.map(data, function(item) {
			return {
			    label: item.name + " (" + item.username + ")",
			    value: item.name,
			    id: item.id
			};
		    });
		    response(output);
		}
	    });
	},
	select: function(event, ui) {
	    $j("#teacher_id").val(ui.item.id);
	}
    });
}
$j(document).ready(function() {
	$j("#clsform").submit(function() {
		$j(this).submit(function() {
		    return false;
		});

		if($j(this).hasClass("grade_range_popup")) {
			return check_grade_range($j(this), $j(this).attr("grademin"), $j(this).attr("grademax"));
		} else {
			return true;
		}
	});
});
