/**
 * This is the directory of classes that has yet to be scheduled
 * Made up of multiple TableRows
 *
 * @param sections
 * @param el
 * @param schedule_assignments
 * @param matrix
 */
function Directory(sections, el, schedule_assignments, matrix) {
    this.sections = sections;
    this.el = el;
    this.schedule_assignments = schedule_assignments;
    this.matrix = matrix;

    /**
     * Render the directory. If an old directory exists, remove it, then re-render it.
     */
    this.render = function(){
        // Remove old classes from the directory
        var oldChildren = this.el.children();
        $j.each(oldChildren, function(c){
            oldChildren[c].hidden = true;
        });

        setTimeout(function(){
            $j.each(oldChildren, function(c){
                oldChildren[c].remove();
                });
        }.bind(this), 0);

        // Create the directory table
        var table = $j("<table/>");
        $j.each(this.sections.filtered_sections(), function(id, section){
            var row = new TableRow(section, $j("<tr/>"), this);
            row.render();
            row.el.appendTo(table);
        }.bind(this))
        table.appendTo(this.el);

    };

    /**
     * Initialize the directory
     */
    this.init = function(){
        // set up handlers
        // Whenever the schedule is changed, re-render the entire directory
        $j("body").on("schedule-changed", this.render.bind(this));
    }
    this.init();

}

/**
 * This is one row in the directory containing a section to be scheduled
 * Includes a Cell that functions as a handle for scheduling the section
 *
 * @param section: The section represented by that row
 * @param el: The element that will form the row
 * @param directory: The directory that contains the row
 *
 * Public methods:
 * @method render()
 */
function TableRow(section, el, directory){
    this.el = el;
    this.section = section;
    this.directory = directory;

    this.cell = new Cell($j("<td class='selectable-cell'/>"), section, null, null, this.directory.matrix);
    this.section.directoryCell = this.cell;
    /**
     * Style el into a row
     */
    this.render = function(){
        var baseURL = directory.sections.getBaseUrlString();
        var autoschedulerLink = "";
        if (has_autoscheduler_frontend === "True") {
            autoschedulerLink = " <a target='_blank' href='" + baseURL +
                "autoscheduler?section=" + this.section.id + "'>Optimize</a>";
        }
        this.el[0].innerHTML = "<td>" + this.section.title +
            " <a target='_blank' href='" + baseURL +
            "manageclass/" + this.section.parent_class +
            "'>Manage</a>" + " <a target='_blank' href='" + baseURL +
            "editclass/" + this.section.parent_class + "'>Edit</a>" +
            " <a target='_blank' href='" + baseURL +
            "classavailability/" + this.section.parent_class + "'>Class Availability</a>" +
            autoschedulerLink + "</td>";
        this.el.append(this.cell.el);
    };
}
