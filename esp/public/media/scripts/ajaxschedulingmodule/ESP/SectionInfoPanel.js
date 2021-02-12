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
                .click(function(evt) {
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
        var commentButton = $j("<button class='sidetoolbar'>" + commentText + "</button>");
        commentButton
            .button()
            .click(function(evt) {
                this.sectionCommentDialog.show(section);
            }.bind(this)
        );
        toolbar.append(commentButton);

        var overrideCheckbox = $j("<input id='schedule-override' type='checkbox'></input>");
        overrideCheckbox.prop('checked', this.override)
            .change(function(box) {
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

    // The content to put on the panel
    var getContent = function(section) {
        var contentDiv = $j("<div class='ui-widget-content'></div>");

        // Make content
        var teachers = this.sections.getTeachersString(section);
        var resources = this.sections.getResourceString(section);

        var content_parts = {};

        if(section.schedulingComment) {
            content_parts['Scheduling Comment'] = section.schedulingComment;
        }

        content_parts['Title'] = section.title;
        content_parts['Teachers'] = teachers;
        content_parts['Class size max'] = section.class_size_max;
        content_parts['Length'] = Math.ceil(section.length);
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
    };

}
