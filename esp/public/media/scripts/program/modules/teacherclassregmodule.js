function check_grade_range(form)
{
    console.log("Checking!");
    var grade_max = $j(form).find('#id_grade_max').val();
    var grade_min = $j(form).find('#id_grade_min').val();
    if (grade_max - grade_min >= 4)
    {
        return confirm("Are you sure you want your class to have grade range "+grade_min+"-"+grade_max+"? \
Managing a class with grade range "+grade_min+"-"+grade_max+" can be more difficult due to the \
difference in maturity levels between middle and high school students. \
Click OK if you are sure this is what you want, or click Cancel to go back \
and change the grade range.");
    }
    else
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
