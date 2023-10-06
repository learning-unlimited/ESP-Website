/**
 * The panel to display information about a section.
 *
 * @param el: The element to shape into the panel
 * @param sections: The sections object of the scheduler
 * @param togglePanel: The panel to hide when this one is shown. May be null.
 */
function SectionInfoPanel(el, sections, togglePanel, sectionCommentDialog) {
    this.el = el;
    this.togglePanel = togglePanel; // The panel that should be hidden when the info panel is shown
    this.sections = sections;
    this.sectionCommentDialog = sectionCommentDialog;
    this.override = false;

    /**
     * Hide the panel and show togglePanel if it exists.
     */
    this.hide = function() {
        this.el.addClass("ui-helper-hidden");
        if(this.togglePanel) {
            this.togglePanel.show();
        }
    };

    /**
     * Show the panel and hide togglePanel if it exists.
     */
    this.show = function() {
        this.el.removeClass("ui-helper-hidden");
        if(this.togglePanel) {
            this.togglePanel.hide();
        }
    };

    /**
     * Helper methods for getting the info for the section
     */

    // The header for the panel
    var getHeader = function(section) {
        var header = $j("<div class='ui-widget-header'>")
        header.append("Information for " + section.emailcode);
        return header;
    };

    // The buttons available for this section
    var getToolbar = function(section) {
        var toolbar = $j("<div>");
        if(this.sections.isScheduled(section)) {
            var unscheduleButton = $j("<button class='sidetoolbar'>Unschedule Section</button>");
            unscheduleButton
                .button()
                .on("click", function(evt) {
                    this.sections.unscheduleSection(section);
                }.bind(this)
            );
            toolbar.append(unscheduleButton);
        }

        var commentText = 'Set Comment';
        if (section.schedulingLocked) {
            commentText = 'Edit Comment or Unlock';
        } else if (section.schedulingComment) {
            commentText = 'Edit Comment';
        }
        // Add a button that shows the sectionCommentDialog
        var commentButton = $j("<button class='sidetoolbar'>" + commentText + "</button>");
        commentButton
            .button()
            .on("click", function(evt) {
                this.sectionCommentDialog.show(section);
            }.bind(this)
        );
        toolbar.append(commentButton);

        var overrideCheckbox = $j("<input id='schedule-override' type='checkbox'></input>");
        overrideCheckbox.prop('checked', this.override)
            .on("change", function(box) {
                var override = $j(box.target).prop("checked");
                // Reload the section to update the availability
                this.sections.unselectSection(override);
                this.sections.selectSection(section);
            }.bind(this)
        );
        toolbar.append(overrideCheckbox);
        toolbar.append($j("<label for='schedule-override'>Override availability</label>"));

        var baseURL = this.sections.getBaseUrlString();
        var autoschedulerLink = "";
        if (has_autoscheduler_frontend === "True") {
            autoschedulerLink = " <a target='_blank' href='" + baseURL +
            "autoscheduler?section=" + section.id + "'>Optimize</a>";
        }
        var links =  $j(
            "<br/><a target='_blank' href='" + baseURL + "manageclass/" + section.parent_class +
                "'>Manage</a>" +
                " <a target='_blank' href='" + baseURL + "editclass/" + section.parent_class +
                "'>Edit</a>" +
                " <a target='_blank' href='" + baseURL + "classavailability/" + section.parent_class +
                "'>Class Availability</a>" +
                autoschedulerLink);
        toolbar.append(links);
        return toolbar;

    }.bind(this);

    var getTeacherLinks = function(section) {
        var teacher_links_list = []
            $j.each(section.teacher_data, function(index, teacher) {
                teacher_links_list.push("<a target='_blank' href='/manage/userview?username=" + encodeURIComponent(teacher.username) + "&program=" + prog_id + "'>" + teacher.first_name + " " + teacher.last_name + "</a>");
            });
        var teacher_links = teacher_links_list.join(", ");
        return $j(teacher_links);
    };

    var getModeratorLinks = function(section) {
        var moderator_links_list = []
            $j.each(section.moderator_data, function(index, moderator) {
                moderator_links_list.push("<a href='#' class='moderator-link' data-moderator='" + moderator.id + "'>" + moderator.first_name + " " + moderator.last_name +
                                          "</a> <button class='moderator-remove' data-moderator='" + moderator.id + "' data-section='" + section.id + "'>Remove</button>");
            });
        var moderator_links = moderator_links_list.join(", ");
        return $j(moderator_links);
    };

    // The content to put on the panel
    var getContent = function(section) {
        var contentDiv = $j("<div class='ui-widget-content'></div>");

        // Make content
        var teacher_links = getTeacherLinks(section);
        var resources = this.sections.getResourceString(section);

        var content_parts = {};

        if(section.schedulingComment) {
            content_parts['Scheduling Comment'] = section.schedulingComment;
        }

        content_parts['Title'] = section.title;
        content_parts['Category'] = this.sections.categories_data[section.category_id].name;
        content_parts['Teachers'] = teacher_links;
        if(has_moderator_module === "True") content_parts[moderator_title + 's'] = getModeratorLinks(section);
        content_parts['Style'] = section.class_style;
        content_parts['Class size max'] = section.class_size_max;
        var length_str = '';
        if(Math.floor(section.length) > 0){
            length_str += Math.floor(section.length);
            length_str += ' hour';
            if(Math.floor(section.length) > 1) length_str += 's';
        }
        if((section.length % 1) * 60 > 0) length_str += ' ' + Math.round((section.length % 1) * 60) + ' minutes';
        content_parts['Length'] = length_str;
        content_parts['Grades'] = section.grade_min + "-" + section.grade_max;
        content_parts['Room Request'] = section.requested_room;
        content_parts['Resource Requests'] = resources;
        content_parts['Flags'] = section.flags;

        if(section.comments) {
            content_parts['Comments'] = section.comments;
        }
        if(section.special_requests && section.special_requests.length > 0) {
            content_parts['Room Requests'] = section.special_requests;
        }

        for(var header in content_parts) {
            var partDiv = $j('<div>');
            partDiv.append('<b>' + header + ': </b>');
            partDiv.append(content_parts[header]);
            contentDiv.append(partDiv);
        }
        contentDiv.append($j('<br><div><b>Click on another section while holding down "Ctrl"/"Cmd" to swap it with this section</b>'));

        return contentDiv;
    }.bind(this);

    /**
     * Display info for a section.
     *
     * @param section: the section to display on the panel
     */
    this.displaySection = function(section) {
        this.el[0].innerHTML = "";
        this.show();
        this.el.append(getHeader(section));
        this.el.append(getToolbar(section));
        this.el.append(getContent(section));
        if(has_moderator_module === "True") {
            $j(".moderator-remove").on("click", function(evt) {
                var mod = this.sections.matrix.moderatorDirectory.getById($j(evt.target).data("moderator"));
                var sec = this.sections.getById($j(evt.target).data("section"));
                this.sections.matrix.moderatorDirectory.selectedModerator = mod;
                this.sections.matrix.moderatorDirectory.unassignModerator(sec);
            }.bind(this));
        }
    };

    var getModeratorHeader = function(moderator) {
        var header = $j("<div class='ui-widget-header'>")
        header.append("Information for " + moderator.first_name + " " + moderator.last_name);
        return header;
    };

    var getModeratorToolbar = function(moderator) {
        var toolbar = $j("<div>");

        var overrideCheckbox = $j("<input id='schedule-override' type='checkbox'></input>");
        overrideCheckbox.prop('checked', this.override)
            .on("change", function(box) {
                var override = $j(box.target).prop("checked");
                // Reload the moderator to update the availability
                this.sections.matrix.moderatorDirectory.unselectModerator(override);
                this.sections.matrix.moderatorDirectory.selectModerator(moderator);
            }.bind(this)
        );
        toolbar.append(overrideCheckbox);
        toolbar.append($j("<label for='schedule-override'>Override availability</label>"));

        var baseURL = this.sections.getBaseUrlString();
        var links =  $j(
            "<br/><a target='_blank' href='" + baseURL +
            "edit_availability?user=" + moderator.username +
            "'>Edit Availability</a>" + " <a target='_blank' href='/manage/userview?username=" +
            moderator.username + "&program=" + prog_id + "'>Userview</a>");
        toolbar.append(links);
        return toolbar;

    }.bind(this);

    // The content to put on the panel for a moderator
    var getModeratorContent = function(moderator) {
        var contentDiv = $j("<div class='ui-widget-content'></div>");

        var content_parts = {};

        content_parts['Will Moderate'] = (moderator.will_moderate)? "Yes" : "No";
        content_parts['Number of Slots'] = moderator.num_slots;
        content_parts['Class Categories'] = moderator.categories.map(cat => this.sections.categories_data[cat].name).join(', ');
        content_parts['Comments'] = moderator.comments;

        for(var header in content_parts) {
            var partDiv = $j('<div>');
            partDiv.append('<b>' + header + ': </b>');
            partDiv.append(content_parts[header]);
            contentDiv.append(partDiv);
        }
        contentDiv.append($j('<br><div><b>Click on a section while holding down "Ctrl"/"Cmd" to assign/unassign this moderator</b>'));

        return contentDiv;
    }.bind(this);

    /**
     * Display info for a moderator.
     *
     * @param moderator: the moderator to display on the panel
     */
    this.displayModerator = function(moderator) {
        this.el[0].innerHTML = "";
        this.show();
        this.el.append(getModeratorHeader(moderator));
        this.el.append(getModeratorToolbar(moderator));
        this.el.append(getModeratorContent(moderator));
    };
}
