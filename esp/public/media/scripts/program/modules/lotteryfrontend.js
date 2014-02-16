// This will hold the last lottery run, in case we want to finalize and save it
var student_sections = '';
var student_ids = '';
var section_ids = '';

function runLotteryThing() {
	$j('#lotterythingstats').html('Loading...');
	var $inputs = $j('#lotteryform :input');
	var post_data = {'csrfmiddlewaretoken': csrf_token()};
	
	$inputs.each(function() {
		if(this.name.indexOf('lottery_') == 0) {
			post_data[this.name] = $j(this).val();
		}
	});
	
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_execute",
		type: "post",
		data: post_data,
		success: function(data) {
			data = data['response'][0];
			student_sections = data['student_sections'];
			student_ids = data['student_ids'];
			section_ids = data['section_ids'];
			$j('#lotterythingstats').html("<pre>" + data['stats'] + "</pre>");
		},
		dataType: 'json'
	});
}

function saveLotteryThing() {
	$j('#lotterythingstats').html('Saving...');
	var post_data = {'csrfmiddlewaretoken': csrf_token(), 'student_sections': student_sections, 'student_ids': student_ids, 'section_ids': section_ids};
	
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_save",
		type: "post",
		data: post_data,
		success: function() {
			$j('#lotterythingstats').html("The lottery assignments has been saved successfully!");
		},
		dataType: 'json'
	});
}

function clearLotteryThing() {
	$j('#lotterythingstats').html('Clearing...');
	var post_data = {'csrfmiddlewaretoken': csrf_token()};
	
	$j.ajax({
		url: "/manage/" + program_url_base + "/lottery_clear",
		type: "post",
		data: post_data,
		success: function() {
			$j('#lotterythingstats').html("The lottery assignments has been clear successfully!");
		},
		dataType: 'json'
	});
}
