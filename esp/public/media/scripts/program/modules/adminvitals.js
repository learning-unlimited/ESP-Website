statsFilled = false;

function fillData(ID, stats)
{
    $field = $j(ID.concat(" > .module_group_body"));
    $field.html('');
    for (var i = 0; i < stats.length; i++)
    {
	$field.append("<strong>"+stats[i][0]+"</strong> &ndash; "+stats[i][1]);
	if (i != stats.length - 1)
	{
	    $field.append("<br />");
	}
    }
    
}

function fillStats(data)
{
    // Pull out the stats data
    stats = json_data.stats;
    vitals = stats.vitals;
    categories = stats.categories;
    grades = stats.grades;
    shirtnum = stats.shirtnum;
    accounting = stats.accounting;

    // Fill in student num data
    fillData("#stats_students", vitals.studentnum)

    // Fill in the teacher num data
    fillData("#stats_teachers", vitals.teachernum)

    // Fill in the volunteer num data
    fillData("#stats_volunteers", vitals.volunteernum)

    if (has_moderator_module === "True") {
        // Fill in the moderator num data
        fillData("#stats_moderators", vitals.moderatornum)
    }

    // Fill in the classes num data
    fillData("#stats_classes", vitals.classnum)

    // Fill in the flags num data
    fillData("#stats_flags", vitals.flagsnum)

    // Fill in the categories table
    $categories = $j("#stats_categories > .module_group_body");
    $categories.html("(Note: Totals include unreviewed classes)"+
		     "<table><tr><th><b>Category</b></th>"+
		     "<th class='smaller'># of subjects</th>"+
		     "<th class='smaller'># of sections</th>"+
		     "<th class='smaller'># of class-hours</th></tr></table>");
    $categorytable = $categories.children("table");
    for (var i = 0; i < categories.data.length; i++)
    {
	$categorytable.append("<tr><th class='smaller'>"+categories.data[i].category+"</th>"+
		"<td>"+categories.data[i].num_subjects+"</td>"+
		"<td>"+categories.data[i].num_sections+"</td>"+
		"<td>"+categories.data[i].num_class_hours+"</td></tr>");
    }

    // Fill in the grades table
    $grades = $j("#stats_grades > .module_group_body");
    $grades.html("(Note: students counted are enrolled in at least one class)"+
	         "<table><tr><th><b>Grade</b></th>"+
		 "<th class='smaller'># of students</th>"+
		 "<th class='smaller'># of subjects</th>"+
		 "<th class='smaller'># of sections</th></tr></table>");
    $gradestable = $grades.children("table");
    for (var i = 0; i < grades.data.length; i++)
    {
	$gradestable.append("<tr><th class='smaller'>"+grades.data[i].grade+"</th>"+
		"<td>"+grades.data[i].num_students+"</td>"+
		"<td>"+grades.data[i].num_subjects+"</td>"+
		"<td>"+grades.data[i].num_sections+"</td></tr>");
    }

    // Fill in the hours num data
    fillData("#stats_hours", vitals.hournum)

    // Fill in the timeslots table
    $timeslots = $j("#stats_timeslots > .module_group_body");
    $timeslots.html('');
    for (var i = 0; i < vitals.timeslots.length; i++)
    {
	$timeslots.append("<strong>"+vitals.timeslots[i].slotname+"</strong> &ndash; <br />"+
		      "<p>Students: "+vitals.timeslots[i].studentcount.count+" / "+vitals.timeslots[i].studentcount.max_count+"<br />"+
		      "Classes: "+vitals.timeslots[i].classcount+
		      "</p>");
    }

    // Fill in the t-shirts table
    $tshirts = $j("#stats_tshirts > .module_group_body");
    html_string = ""
    for (var group of shirtnum.data)
    {
        if (group.name == "Assigned Moderators")
        {
            group_name = "Assigned " + shirtnum.moderator_title + "s";
        } else 
        {
            group_name = group.name;
        }
        var shirtsizes = group.shirt_sizes;
        html_string = html_string.concat("<table><tr><th colspan='"+(shirtsizes.length+1)+"'>"+group_name+" T-Shirts</th></tr>");
        // Sizes header
        html_string = html_string.concat("<tr><td></td>");
        for (var i = 0; i < shirtsizes.length; i++)
        {
            html_string = html_string.concat("<th class='smaller'>"+shirtsizes[i]+"</th>");
        }
        html_string = html_string.concat("</tr>");
        // Types
        var curDist = group.distribution;
        for (var i = 0; i < curDist.length; i++)
        {
            //  console.log(curDist);
            html_string = html_string.concat("<tr><th class='smaller'>"+curDist[i].type+"</th>");
            for (var j = 0; j < curDist[i].counts.length; j++)
            {
                html_string = html_string.concat("<td>"+curDist[i].counts[j]+"</td>");
            }
            html_string = html_string.concat("</tr>");
        }
        html_string = html_string.concat("</table><br>");
    }
    $tshirts.html(html_string);
    
    //  Fill in the accounting table
    $accounting = $j("#stats_accounting > .module_group_body");
    $accounting.html("<strong>Number of credit card payments</strong>: " + accounting.data.num_payments + "<br />");
    $accounting.append("<strong>Total amount of credit card payments</strong>: $" + accounting.data.total_payments.toFixed(2));
}

function getStats()
{
    // Check/update the global flag
    if(statsFilled) { return; }
    statsFilled = true;

    json_fetch(["stats"], fillStats, json_data, function() { alert('Error loading stats data from server'); });
}
