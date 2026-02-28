var csrftoken = $j.cookie('esp_csrftoken');

$j.ajaxSetup({
    crossDomain: false,
    beforeSend: function(xhr, settings) {
        if (settings.type == 'POST') {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

var tl, program_base_url;

$j(function () {
    tl = $j('#tl').val();
    program_base_url = '/' + tl + '/' + $j('#program-base-url').val();
    $j('#loading').hide();
    $j('#students-list thead').append(
        make_table_header_row()
    );
    $j('#save-button').prop('disabled', true).on("click", save_changes);
    $j('#refresh-button').on("click", function () {
        var class_id = $j('#class-dropdown').val();
        load_class(class_id);
    });
    $j('#class-dropdown').on("change", function () {
        var class_id = $j(this).val();
        if (load_class(class_id)) {
            $j(this).data('prev', class_id);
        }
        else {
            $j(this).val($j(this).data('prev'));
        }
    });
    $j(window).on('beforeunload', function () {
        if (!$j.isEmptyObject(unsaved_changes)) {
            return 'You have unsaved changes; if you leave this page, they will be lost.';
        }
    });
});

function load_class(class_id, prev) {
    if (!$j.isEmptyObject(unsaved_changes) && !confirm('You have unsaved changes; if you continue, they will be lost.')) {
        return false;
    }
    discard_changes();
    $j('#students-list tbody').empty();
    if (class_id !== '') {
        $j('#loading').show();
        $j.getJSON(program_base_url + '/apps/' + class_id, populate_table);
    }
    return true;
}

function load_app(app_id) {
    $j('#student-detail').empty();
    if (app_id !== '') {
        $j.get(program_base_url + '/app/' + app_id, function (data) {
            $j('#student-detail').html(data);
        });
    }
    return false;
}

function populate_table(data) {
    $j('#loading').hide();
    $j('#students-list tbody').empty();
    data.apps.forEach(function (app) {
        $j('#students-list tbody').append(
            make_table_row(app, data.apps.length)
        );
    });
    sort_table();
}

function make_table_header_row() {
    var $row = $j('<tr></tr>');
    if (tl == 'teach') {
        $row.append(
            $j('<th></th>').text('Name'),
            $j('<th></th>').text('Rating'),
            $j('<th></th>').text('Rank'),
            $j('<th></th>').text('Comments')
        );
    }
    else if (tl == 'manage') {
        $row.append(
            $j('<th></th>').text('Name'),
            $j('<th></th>').text('Admin Status'),
            $j('<th></th>').text('Admin Comments'),
            $j('<th></th>').text('Teacher Rating'),
            $j('<th></th>').text('Teacher Rank'),
            $j('<th></th>').text('Teacher Comments'),
            $j('<th></th>').text('Student Preference'),
            $j('<th></th>').text('Decision Status'),
            $j('<th></th>').text('Decision Action')
        );
    }
    return $row;
}

function make_name_cell(app) {
    var $name = $j('<a></a>')
	.prop('href', program_base_url + '/app/' + app.id)
        .addClass('name')
        .text(app.user.name);
    if (tl == 'manage') { // open in new window
	$name.prop('target', '_blank');
    }
    else { // open in side pane
        $name.on("click", function () {
            load_app(app.id);
            return false;
        });
    }
    return $name;
}

function make_teacher_rating_cell(app, readonly) {
    var $teacher_rating = $j('<select></select>')
        .addClass('teacher_rating')
        .append(
            $j('#teacher-rating-choices').children('option').clone()
        )
        .val(app.teacher_rating || '')
        .on("change", sort_table)
        .on("change", function () {
            var val = parseInt($j(this).val());
            update(app.id, {'teacher_rating': val});
        })
        .prop('disabled', !!readonly);
    return $teacher_rating;
}

function make_teacher_ranking_cell(app, num_apps, readonly) {
    var $teacher_ranking = $j('<select><option></option></select>')
        .addClass('teacher_ranking');
    for (var i = 1; i <= num_apps; i++) {
        $teacher_ranking.append( $j('<option></option>').text(i) );
    };
    $teacher_ranking.val(app.teacher_ranking || '')
        .on("change", sort_table)
        .on("change", function () {
            var val = parseInt($j(this).val());
            update(app.id, {'teacher_ranking': val});
        })
        .prop('disabled', !!readonly);
    return $teacher_ranking;
}

function make_teacher_comments_cell(app, readonly) {
    var $textarea = $j('<textarea rows="5" cols="50" />');
    var $teacher_comments_dialog = $j('<div title="Comments"></div>').append(
        readonly ? '<p>View teacher comment below.</p>'
            : '<p>Type your comment below.</p>',
        $textarea
    );
    var $teacher_comments = $j('<div></div>')
        .addClass('teacher_comments')
        .on("click", function () {
            var text = $teacher_comments.data('comment');
            $teacher_comments_dialog.dialog('open');
            $textarea.val(text).focus();
        });
    $teacher_comments.set_comment = function (comment) {
        if (readonly) {
            this.data('comment', comment)
                .text(comment)
        }
        else {
            this.data('comment', comment)
                .text(comment || '(click to add comment)')
                .css('color', comment ? '' : '#aaa');
        }
    }
    $teacher_comments.set_comment(app.teacher_comment)
    $teacher_comments_dialog.dialog({
        autoOpen: false,
        modal: true,
        width: 'auto',
        buttons: readonly ? {
            'Close': function () {
                $j(this).dialog('close');
            }
        } : {
            'Save': function () {
                var text = $textarea.val();
                $teacher_comments.set_comment(text);
                update(app.id, {'teacher_comment': text});
                $(this).dialog('close');
            },
            'Cancel': function () {
                $j(this).dialog('close');
            }
        }
    });
    return $teacher_comments;
}

function make_admin_status_cell(app) {
    var $admin_status = $j('<select></select>')
        .addClass('admin_status')
        .append(
            $j('#admin-status-choices').children('option').clone()
        )
        .val(app.admin_status)
        .on("change", function () {
            var val = parseInt($j(this).val());
            update(app.id, {'admin_status': val});
        });
    return $admin_status;
}

function make_admin_comments_cell(app) {
    var $textarea = $j('<textarea rows="5" cols="50" />');
    var $admin_comments_dialog = $j('<div title="Comments"></div>').append(
        '<p>Type your comment below.</p>',
        $textarea
    );
    var $admin_comments = $j('<div></div>')
        .addClass('admin_comments')
        .data('comment', app.admin_comment || '')
        .text(app.admin_comment || '(click to add comment)')
        .css('color', app.admin_comment ? '' : '#aaa')
        .on("click", function () {
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
                $j(this).dialog('close');
            },
            'Cancel': function () {
                $j(this).dialog('close');
            }
        }
    });
    return $admin_comments;
}

function make_student_preference_cell(app) {
    var $student_preference = $j('<span></span>')
        .addClass('student_preference')
        .text(app.student_preference);
    return $student_preference;
}

function make_decision_status_cell(app) {
    var $decision_status = $j('<div></div>')
        .addClass('decision_status');
    app.decision_status.split('\n').forEach(function (line) {
        $j('<div></div>').text(line).appendTo($decision_status);
    });
    return $decision_status;
}

function make_decision_action_cell(app) {
    var $decision_action = $j('<select></select>')
        .addClass('decision_action')
        .append(
            $j('#decision-action-choices').children('option').clone()
        )
        .on("change", function () {
            var val = $j(this).val();
            update(app.id, {'decision_action': val});
        });
    return $decision_action;
}

function make_table_row(app, num_apps) {
    var $row = $j('<tr></tr>');

    if (tl == 'teach') {
        var cells = [
            make_name_cell(app),
            make_teacher_rating_cell(app),
            make_teacher_ranking_cell(app, num_apps),
            make_teacher_comments_cell(app)
        ];
        cells.forEach(function (cell) {
            $j('<td></td>').append(cell).appendTo($row);
        });
        $row.data('teacher_rating', cells[1]);
        $row.data('teacher_ranking', cells[2]);
    }
    else if (tl == 'manage') {
        var cells = [
            make_name_cell(app),
            make_admin_status_cell(app),
            make_admin_comments_cell(app),
            make_teacher_rating_cell(app, true),
            make_teacher_ranking_cell(app, num_apps, true),
            make_teacher_comments_cell(app, true),
            make_student_preference_cell(app),
            make_decision_status_cell(app),
            make_decision_action_cell(app)
        ];
        cells.forEach(function (cell) {
            $j('<td></td>').append(cell).appendTo($row);
        });
        $row.data('teacher_rating', cells[3]);
        $row.data('teacher_ranking', cells[4]);
    }

    return $row;
}

function sort_table() {
    var elements = $j('#students-list tbody tr');
    elements.sort(function (a, b) {
        var $a = $j(a), $b = $j(b);
        var a_val = parseInt($a.data('teacher_rating').val()) || 1/0;
        var b_val = parseInt($b.data('teacher_rating').val()) || 1/0;
        if (a_val !== b_val) {
            return a_val - b_val;
        }
        a_val = parseInt($a.data('teacher_ranking').val()) || 1/0;
        b_val = parseInt($b.data('teacher_ranking').val()) || 1/0;
        return a_val - b_val;
    });
    $j('#students-list tbody').append(elements);
}

var unsaved_changes = {};
var pending_changes = {};

function update(app_id, change) {
    unsaved_changes[app_id] = $j.extend(unsaved_changes[app_id] || {},
                                       change);
    if ($j.isEmptyObject(pending_changes)) {
        $j('#save-button').prop('disabled', false).text('Save');
    }
}

function discard_changes() {
    $j('#save-button').prop('disabled', true).text('Save');
    unsaved_changes = {};
    pending_changes = {};
}

function save_changes() {
    $j('#save-button').prop('disabled', true).text('Saving...');
    if (!$j.isEmptyObject(pending_changes)) {
        // can't save while there are pending changes
        console.log('foo');
        return;
    }
    pending_changes = $j.extend({}, unsaved_changes)
    unsaved_changes = {};
    var post_data = { changes: JSON.stringify(pending_changes) };
    var success = function (data) {
        data.updated.forEach(function (app_id) {
            delete pending_changes[app_id];
        });
        if ($a.isEmptyObject(pending_changes)) {
            $j('#save-button').prop('disabled', true).text('Saved');
        }
        else {
            save_error();
        }
    };
    var save_error = function () {
        Object.keys(pending_changes).forEach(function (app_id) {
            unsaved_changes[app_id] = $j.extend(pending_changes[app_id],
                                               unsaved_changes[app_id]);
            delete pending_changes[app_id];
        });
        $j('#save-button').prop('disabled', false).text('Save');
        alert('Encountered an error while saving.');
    };
    $j.post(program_base_url + '/update_apps', post_data)
        .done(success).fail(save_error);
}

