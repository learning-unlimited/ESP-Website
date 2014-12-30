function SectionInfoPanel(el, teachers, sections, togglePanel) {
    this.el = el;
    this.togglePanel = togglePanel; // The panel that should be hidden when the info panel is shown
    this.teachers = teachers;
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


    var getHeader = function(section) {
        var header = $j("<div class='ui-widget-header'>")
        header.append("Information for " + section.emailcode);
        return header;
    };

    var getToolbar = function(section) {
        var toolbar = $j("<div>");
        var unscheduleButton = $j("<button id='unschedule'>Unschedule Section</button></br>");
        unscheduleButton
            .button()
            .click(function(evt) {
                this.sections.unscheduleSection(section);
            }.bind(this));
        toolbar.append(unscheduleButton);
        return toolbar;
        
    }.bind(this);

    var getContent = function(section) {
        var contentDiv = $j("<div class='ui-widget-content'></div>");

        // Make content
        var teacher_list = []
        $j.each(section.teachers, function(index, teacher_id) {
            var teacher = this.teachers[teacher_id]
            teacher_list.push(teacher.first_name + " " + teacher.last_name);
        }.bind(this));
        var teachers = teacher_list.join(", ");
        
        var content_parts = [
            "Title: " + section.title,
            "Teachers: " + teachers,
            "Class size max: " + section.class_size_max,
	        "Length: " + Math.ceil(section.length),
            "Grades: " + section.grade_min + "-" + section.grade_max,
        ]

        contentDiv.append(content_parts.join("</br>"));

        return contentDiv;
    }.bind(this);

    /**
     * Display info for a class.
     */
    this.displaySection = function(section) {
        this.el[0].innerHTML = "";
        this.show();
        this.el.append(getHeader(section));
        this.el.append(getToolbar(section));
        this.el.append(getContent(section));
    };

}
