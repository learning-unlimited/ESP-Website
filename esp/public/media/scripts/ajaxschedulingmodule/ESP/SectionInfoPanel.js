/**
 * The panel to display information about a section.
 * 
 * @param el: The element to shape into the panel
 * @param sections: The sections object of the scheduler
 * @param togglePanel: The panel to hide when this one is shown. May be null.
 */
function SectionInfoPanel(el, sections, togglePanel) {
    this.el = el;
    this.togglePanel = togglePanel; // The panel that should be hidden when the info panel is shown
    this.sections = sections;

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
        var unscheduleButton = $j("<button id='unschedule'>Unschedule Section</button></br>");
        unscheduleButton
            .button()
            .click(function(evt) {
                this.sections.unscheduleSection(section);
            }.bind(this));
        var baseURL = this.sections.getBaseUrlString();
	    var links =  $j(
            "<a target='_blank' href='" + baseURL + "manageclass/" + section.parent_class + 
                "'>Manage</a>" + 
                " <a target='_blank' href='" + baseURL + "editclass/" + section.parent_class +
                "'>Edit</a>");
        toolbar.append(unscheduleButton);
        toolbar.append(links);
        return toolbar;
        
    }.bind(this);

    // The content to put on the panel
    var getContent = function(section) {
        var contentDiv = $j("<div class='ui-widget-content'></div>");

        // Make content
        var teachers = this.sections.getTeachersString(section);
        var resources = this.sections.getResourceString(section);
        
        var content_parts = [
            "Title: " + section.title,
            "Teachers: " + teachers,
            "Class size max: " + section.class_size_max,
	        "Length: " + Math.ceil(section.length),
            "Grades: " + section.grade_min + "-" + section.grade_max,
            "Resource Requests: " + resources,
            "Flags: " + section.flags,
        ]
        if(section.comments) {
            content_parts.push("Comments: " + section.comments);
        }
        if(section.special_requests && section.special_requests.length > 0) {
            content_parts.push("Room Requests: " + section.special_requests);
        }
	

        contentDiv.append(content_parts.join("</br>"));

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
