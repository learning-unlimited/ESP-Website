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

function load_app(app_id) {
    $('#student-detail').empty();
    if (app_id !== '') {
        $.getJSON(program_base_url + '/app/' + app_id, function (data) {
            var converter = Markdown.getSanitizingConverter();
            var html = converter.makeHtml(data.app);
            $('#student-detail').html(html);
        });
    }
    return false;
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

function make_name_cell(app) {
    var $name = $('<a href="#!"></a>')
        .addClass('name')
        .text(app.user.name)
        .click(function () {
            load_app(app.id);
            return false;
        });
    return $name;
}

function make_teacher_rating_cell(app, readonly) {
    var $teacher_rating = $('<select></select>')
        .addClass('teacher_rating')
        .append(
            $('#teacher-rating-choices').children('option').clone()
        )
        .val(app.teacher_rating || '')
        .change(resort_table)
        .change(function () {
            update(app.id, {'teacher_rating': $(this).val()});
        });
    return $teacher_rating;
}

function make_teacher_ranking_cell(app, num_apps) {
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
    return $teacher_ranking;
}

function make_teacher_comments_cell(app) {
    var $textarea = $('<textarea rows="5" cols="50" />');
    var $teacher_comments_dialog = $('<div title="Comments"></div>').append(
        '<p>Type your comment below.</p>',
        $textarea
    );
    var $teacher_comments = $('<div></div>')
        .addClass('teacher_comments')
        .data('comment', app.teacher_comment || '')
        .text(app.teacher_comment || '(click to add comment)')
        .css('color', app.teacher_comment ? '' : '#aaa')
        .click(function () {
            var text = $teacher_comments.data('comment');
            $teacher_comments_dialog.dialog('open');
            $textarea.val(text).focus();
        });
    $teacher_comments_dialog.dialog({
        autoOpen: false,
        modal: true,
        width: 'auto',
        buttons: {
            'Save': function () {
                var text = $textarea.val();
                $teacher_comments.data('comment', text)
                    .text(text || '(click to add comment)')
                    .css('color', text ? '' : '#aaa');
                update(app.id, {'teacher_comment': text});
                $(this).dialog('close');
            },
            'Cancel': function () {
                $(this).dialog('close');
            }
        }
    });
    return $teacher_comments;
}

function make_admin_status_cell(app) {
    var $admin_status = $('<select></select>')
        .addClass('admin_status')
        .append(
            $('#admin-status-choices').children('option').clone()
        )
        .val(app.admin_status)
        .change(function () {
            update(app.id, {'admin_status': $(this).val()});
        });
    return $admin_status;
}

function make_admin_comments_cell(app) {
    var $textarea = $('<textarea rows="5" cols="50" />');
    var $admin_comments_dialog = $('<div title="Comments"></div>').append(
        '<p>Type your comment below.</p>',
        $textarea
    );
    var $admin_comments = $('<div></div>')
        .addClass('admin_comments')
        .data('comment', app.admin_comment || '')
        .text(app.admin_comment || '(click to add comment)')
        .css('color', app.admin_comment ? '' : '#aaa')
        .click(function () {
            var text = $admin_comments.data('comment');
            $admin_comments_dialog.dialog('open');
            $textarea.val(text).focus();
        });
    $admin_comments_dialog.dialog({
        autoOpen: false,
        modal: true,
        width: 'auto',
        buttons: {
            'Save': function () {
                var text = $textarea.val();
                $admin_comments.data('comment', text)
                    .text(text || '(click to add comment)')
                    .css('color', text ? '' : '#aaa');
                update(app.id, {'admin_comment': text});
                $(this).dialog('close');
            },
            'Cancel': function () {
                $(this).dialog('close');
            }
        }
    });
    return $admin_comments;
}

function make_student_preference_cell(app) {
    var $student_preference = $('<span></span>')
        .addClass('student_preference')
        .text(app.student_preference);
    return $student_preference;
}

function make_admission_status_cell(app) {
    var $admission_status = $('<select></select>')
        .addClass('admission_status')
        .append(
            $('#admission-status-choices').children('option').clone()
        )
        .val(app.admission_status)
        .change(function () {
            update(app.id, {'admission_status': $(this).val()});
        });
    return $admission_status;
}

function make_table_row(app, num_apps) {
    var $row = $('<tr></tr>');

    if (tl == 'teach') {
        var cells = [
            make_name_cell(app),
            make_teacher_rating_cell(app),
            make_teacher_ranking_cell(app, num_apps),
            make_teacher_comments_cell(app)
        ];
        cells.forEach(function (cell) {
            $('<td></td>').append(cell).appendTo($row);
        });
        $row.data('teacher_rating', cells[1]);
        $row.data('teacher_ranking', cells[2]);
    }
    else if (tl == 'manage') {
        var cells = [
            make_name_cell(app),
            make_admin_status_cell(app),
            make_admin_comments_cell(app),
            make_teacher_rating_cell(app),
            make_teacher_ranking_cell(app),
            make_teacher_comments_cell(app),
            make_student_preference_cell(app),
            make_admission_status_cell(app)
        ];
        cells.forEach(function (cell) {
            $('<td></td>').append(cell).appendTo($row);
        });
        $row.data('teacher_rating', cells[3]);
        $row.data('teacher_ranking', cells[4]);
    }

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
