/*
 * Admin JS for TemplateOverride add/change form (issue #2879).
 *
 * Adds a "Load default template" button next to the template name field.
 * Clicking it fetches the on-disk default content for that template and
 * pre-populates the content textarea, saving the admin the step of
 * manually copying the file from GitHub.
 */
(function ($) {
    $(document).ready(function () {
        var nameField = $('#id_name');
        var contentField = $('#id_content');

        if (!nameField.length || !contentField.length) {
            return;
        }

        var button = $('<input>', {
            type: 'button',
            id: 'load-default-template-btn',
            value: 'Load default template'
        });

        nameField.after(button);

        button.on('click', function () {
            var templateName = nameField.val().trim();
            if (!templateName) {
                alert('Please enter a template name before loading the default.');
                return;
            }

            if (contentField.val().trim()) {
                if (!confirm('The content field already has content. Overwrite it with the default template?')) {
                    return;
                }
            }

            $.ajax({
                url: '/manage/templateoverride/default_content/',
                data: {name: templateName},
                success: function (data) {
                    contentField.val(data.content);
                },
                error: function (xhr) {
                    var msg;
                    try {
                        msg = JSON.parse(xhr.responseText).error;
                    } catch (e) {
                        msg = 'Could not load default template.';
                    }
                    alert('Error: ' + msg);
                }
            });
        });
    });
}(django.jQuery));
