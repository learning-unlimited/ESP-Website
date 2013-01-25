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
        })

    var $rating = $('<select><option></option></select>')
        .addClass('rating')
        .append(
            $('<option></option>').val(1).text('Green'),
            $('<option></option>').val(2).text('Yellow'),
            $('<option></option>').val(3).text('Red')
        )
        .val(app.rating || '')
        .change(resort_table)
        .change(function () {
            update(app.id, {'rating': $(this).val()});
        });

    var $ranking = $('<select><option></option></select>')
        .addClass('ranking');
    for (var i = 1; i <= num_apps; i++) {
        $ranking.append( $('<option></option>').text(i) );
    };
    $ranking.val(app.ranking || '')
        .change(resort_table)
        .change(function () {
            update(app.id, {'ranking': $(this).val()});
        });

    var $comments = $('<div></div>')
        .addClass('comments')
        .data('comment', app.comment || '')
        .text(app.comment || '(click to add comment)')
        .css('color', app.comment ? '' : '#aaa')
        .click(function () {
            var text = $comments.data('comment');
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
                $comments.data('comment', text)
                    .text(text || '(click to add comment)')
                    .css('color', text ? '' : '#aaa');
                update(app.id, {'comment': text});
                $dialog.close();
            });
            $cancel.click(function () {
                $dialog.close();
            });
            $textarea.focus();
        })

    $row.append(
        $('<td></td>').append($name),
        $('<td></td>').append($rating),
        $('<td></td>').append($ranking),
        $('<td></td>').append($comments)
    )
    $row.data('rating', $rating);
    $row.data('ranking', $ranking);

    return $row;
}

function sort_table() {
    var elements = $('#students-list tbody tr');
    elements.sort(function (a, b) {
        var $a = $(a), $b = $(b);
        var a_val = parseInt($a.data('rating').val()) || 1/0;
        var b_val = parseInt($b.data('rating').val()) || 1/0;
        if (a_val !== b_val) {
            return a_val - b_val;
        }
        a_val = parseInt($a.data('ranking').val()) || 1/0;
        b_val = parseInt($b.data('ranking').val()) || 1/0;
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
        var a_val = parseInt($a.data('rating').val()) || 1/0;
        var b_val = parseInt($b.data('rating').val()) || 1/0;
        if (a_val < b_val) {
            $a.insertBefore($b);
            return;
        }
        else if (a_val > b_val) {
            continue;
        }
        a_val = parseInt($a.data('ranking').val()) || 1/0;
        b_val = parseInt($b.data('ranking').val()) || 1/0;
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
