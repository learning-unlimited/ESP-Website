function setup_autocomplete()
{
    $j("#student_username").autocomplete({
	source: function(request, response) {
            $j.ajax({
		url: "/learn/"+base_url+"/studentlookup/",
		dataType: "json",
		data: {username: request.term},
		success: function(data) {
		    var output = $j.map(data, function(item) {
			return {
			    label: item.username + " (grade " + item.grade + ")",
			    value: item.username,
			    id: item.id
			};
		    });
		    response(output);
		}
	    });
	},
	select: function(event, ui) {
	    $j("#student_id").val(ui.item.id);
	}
    });
}