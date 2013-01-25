var csrftoken = $.cookie('csrftoken');

$.ajaxSetup({
    crossDomain: false,
    beforeSend: function(xhr, settings) {
        if (settings.type == 'POST') {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

var tl, program_base_url;

$(function () {
    tl = $('#tl').val();
    program_base_url = '/' + tl + '/' + $('#program-base-url').val();
    $('#loading').hide();
    $('#students-list thead').append(
	make_table_header_row()
    );
    $('#class-dropdown').change(function () {
        var class_id = $(this).val();
        history.pushState(null, '', program_base_url + '/admissions/' + class_id);
        load_class(class_id);
    });
    $(window).bind('popstate', function () {
        var class_id = window.location.href.split('/')[7] || '';
        $('#class-dropdown').val(class_id);
        load_class(class_id);
    });
});

function load_class(class_id) {
    $('#students-list tbody').empty();
    if (class_id !== '') {
        $('#loading').show();
        $.getJSON(program_base_url + '/apps/' + class_id, populate_table);
    }
}

function populate_table(data) {
    $('#loading').hide();
    $('#students-list tbody').empty();
    data.apps.forEach(function (app) {
        $('#students-list tbody').append(
            make_table_row(app, data.apps.length)
        );
    });
    sort_table();
}

function make_table_header_row() {
    var $row = $('<tr></tr>');
    if (tl == 'teach') {
	$row.append(
            $('<th></th>').text('Name'),
            $('<th></th>').text('Rating'),
            $('<th></th>').text('Rank'),
            $('<th></th>').text('Comments')
	);
    }
    else if (tl == 'manage') {
	$row.append(
            $('<th></th>').text('Name'),
	    $('<th></th>').text('Admin Status'),
	    $('<th></th>').text('Admin Comments'),
            $('<th></th>').text('Teacher Rating'),
            $('<th></th>').text('Teacher Rank'),
            $('<th></th>').text('Teacher Comments'),
	    $('<th></th>').text('Student Preference'),
	    $('<th></th>').text('Decision')
	);
    }
    return $row;
}

function make_table_row(app, num_apps) {
    var $row = $('<tr></tr>');

    var $name = $('<a href="#!"></a>')
        .addClass('name')
        .text(app.user.name)
        .click(function () {
            var converter = Markdown.getSanitizingConverter();
            var html = converter.makeHtml(app.content);
            $('#student-detail').html(html);
            return false;
        });

    var $teacher_rating = $('<select><option></option></select>')
        .addClass('teacher_rating')
        .append(
	    $('#teacher-rating-choices').children('option').clone()
        )
        .val(app.teacher_rating || '')
        .change(resort_table)
        .change(function () {
            update(app.id, {'teacher_rating': $(this).val()});
        });

    var $teacher_ranking = $('<select><option></option></select>')
        .addClass('teacher_ranking');
    for (var i = 1; i <= num_apps; i++) {
        $teacher_ranking.append( $('<option></option>').text(i) );
    };
    $teacher_ranking.val(app.teacher_ranking || '')
        .change(resort_table)
        .change(function () {
            update(app.id, {'teacher_ranking': $(this).val()});
        });

    var $teacher_comments = $('<div></div>')
        .addClass('teacher_comments')
        .data('comment', app.teacher_comment || '')
        .text(app.teacher_comment || '(click to add comment)')
        .css('color', app.teacher_comment ? '' : '#aaa')
        .click(function () {
            var text = $teacher_comments.data('comment');
            var $textarea = $('<textarea rows="5" cols="50" />').val(text);
            var $save = $('<button />').text('Save');
            var $cancel = $('<button />').text('Cancel');
            var $dialog = Dialog.showDialog(Dialog, {
                content: [
                    'Type your comment below.',
                    '<br />',
                    $textarea,
                    '<br />',
                    $save,
                    $cancel,
                ]
            });
            $save.click(function () {
                var text = $textarea.val();
                $teacher_comments.data('comment', text)
                    .text(text || '(click to add comment)')
                    .css('color', text ? '' : '#aaa');
                update(app.id, {'teacher_comment': text});
                $dialog.close();
            });
            $cancel.click(function () {
                $dialog.close();
            });
            $textarea.focus();
        });

    if (tl == 'manage') {
	var $admin_status = $('<select></select>')
	    .addClass('admin_status')
	    .append(
		$('#admin-status-choices').children('option').clone()
	    )
	    .val(app.admin_status)
	    .change(function () {
		update(app.id, {'admin_status': $(this).val()});
	    });
	var $admin_comments = $('<div></div>')
	    .addClass('admin_comments')
	    .data('comment', app.admin_comment || '')
	    .text(app.admin_comment || '(click to add comment)')
	    .css('color', app.admin_comment ? '' : '#aaa')
	    .click(function () {
		var text = $admin_comments.data('comment');
		var $textarea = $('<textarea rows="5" cols="50" />').val(text);
		var $save = $('<button />').text('Save');
		var $cancel = $('<button />').text('Cancel');
		var $dialog = Dialog.showDialog(Dialog, {
		    content: [
			'Type your comment below.',
			'<br />',
			$textarea,
			'<br />',
			$save,
			$cancel,
		    ]
		});
		$save.click(function () {
		    var text = $textarea.val();
		    $admin_comments.data('comment', text)
                    .text(text || '(click to add comment)')
                    .css('color', text ? '' : '#aaa');
                update(app.id, {'admin_comment': text});
                $dialog.close();
            });
            $cancel.click(function () {
                $dialog.close();
            });
            $textarea.focus();
        });
	var $student_preference = $('<div></div>')
	    .addClass('student_preference')
	    .text(app.student_preference);
	var $admission_status = $('<select></select>')
	    .addClass('admission_status')
	    .append(
		$('#admission-status-choices').children('option').clone()
	    )
	    .val(app.admission_status)
	    .change(function () {
		update(app.id, {'admission_status': $(this).val()});
	    });
    }

    if (tl == 'teach') {
	$row.append(
            $('<td></td>').append($name),
            $('<td></td>').append($teacher_rating),
            $('<td></td>').append($teacher_ranking),
            $('<td></td>').append($teacher_comments)
	);
    }
    else if (tl == 'manage') {
	$row.append(
            $('<td></td>').append($name),
	    $('<td></td>').append($admin_status),
	    $('<td></td>').append($admin_comments),
            $('<td></td>').append($teacher_rating),
            $('<td></td>').append($teacher_ranking),
            $('<td></td>').append($teacher_comments),
            $('<td></td>').append($student_preference),
	    $('<td></td>').append($admission_status)
	);
    }
    $row.data('teacher_rating', $teacher_rating);
    $row.data('teacher_ranking', $teacher_ranking);

    return $row;
}

function sort_table() {
    var elements = $('#students-list tbody tr');
    elements.sort(function (a, b) {
        var $a = $(a), $b = $(b);
        var a_val = parseInt($a.data('teacher_rating').val()) || 1/0;
        var b_val = parseInt($b.data('teacher_rating').val()) || 1/0;
        if (a_val !== b_val) {
            return a_val - b_val;
        }
        a_val = parseInt($a.data('teacher_ranking').val()) || 1/0;
        b_val = parseInt($b.data('teacher_ranking').val()) || 1/0;
        return a_val - b_val;
    });
    $('#students-list tbody').append(elements);
}

function resort_table() {
    var $a = $(this).parents('tr', '#students-list tbody');
    var orig_i = $('#students-list tbody tr').index($a);
    $a.detach();
    var elements = $('#students-list tbody tr');
    for (var i = 0; i < elements.length; i++) {
        var $b = $(elements[i]);
        var a_val = parseInt($a.data('teacher_rating').val()) || 1/0;
        var b_val = parseInt($b.data('teacher_rating').val()) || 1/0;
        if (a_val < b_val) {
            $a.insertBefore($b);
            return;
        }
        else if (a_val > b_val) {
            continue;
        }
        a_val = parseInt($a.data('teacher_ranking').val()) || 1/0;
        b_val = parseInt($b.data('teacher_ranking').val()) || 1/0;
        if (a_val < b_val || a_val == b_val && orig_i <= i) {
            $a.insertBefore($b);
            return;
        }
    }
    $('#students-list tbody').append($a);
}

function update(app_id, change) {
    $.post(program_base_url + '/update_app/' + app_id,
           change,
           function () {
               TransientMessage.showMessage('Saved');
           });
}
