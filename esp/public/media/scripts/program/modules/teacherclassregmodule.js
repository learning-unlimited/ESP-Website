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

var sectionNums = JSON.parse(document.getElementById('section-numbers-per-duration').textContent);

function updateMaxSections(){
//{
	//var sectionNums = JSON.parse(document.getElementById('section-numbers-per-duration').textContent);
	var num_sections_cur = $j("#id_num_sections");
	var maxSections = sectionNums[$j("#id_duration").val()];
	
	num_sections_cur.empty();
	
	for (let i = 0; i <= maxSections; i++) {
		if (i == 0){
			num_sections_cur.append('<option value= > </option>');
		}
		else {
			num_sections_cur.append('<option value='+ i +' >' + String(i) + '</option>');
		}
	}
//}
}

$j(function(){
	var duration = $j("#id_duration");
	duration.on("change", function(){
		updateMaxSections();
	})
});


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

    $j("[name=moderator_name]").autocomplete({
	source: function(request, response) {
            $j.ajax({
		url: "/teach/"+base_url+"/moderatorlookup/",
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
	    $j("#moderator_id_" + $j(this).data("secid")).val(ui.item.id);
	}
    });
}
