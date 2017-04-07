statsFilled = false;

function fillStats(data)
{
    // Pull out the stats data
    stats = json_data.stats;
    vitals = stats.vitals;
    categories = stats.categories;
    grades = stats.grades;
    shirtnum = stats.shirtnum;
    splashinfo = stats.splashinfo;
    accounting = stats.accounting;

    // Fill in student num data
    $studentnum = $j("#stats_students > .module_group_body");
    $studentnum.html('');
    for (var i = 0; i < vitals.studentnum.length; i++)
    {
	$studentnum.append("<strong>"+vitals.studentnum[i][0]+"</strong> &ndash; "+vitals.studentnum[i][1]);
	if (i != vitals.studentnum.length - 1)
	{
	    $studentnum.append("<br />");
	}
    }

    // Fill in the teacher num data
    $teachernum = $j("#stats_teachers > .module_group_body");
    $teachernum.html('');
    for (var i = 0; i < vitals.teachernum.length; i++)
    {
	$teachernum.append("<strong>"+vitals.teachernum[i][0]+"</strong> &ndash; "+vitals.teachernum[i][1]);
	if (i != vitals.teachernum.length - 1)
	{
	    $teachernum.append("<br />");
	}
    }

    // Fill in the volunteer num data
    $volunteernum = $j("#stats_volunteers > .module_group_body");
    $volunteernum.html('');
    for (var i = 0; i < vitals.volunteernum.length; i++)
    {
	$volunteernum.append("<strong>"+vitals.volunteernum[i][0]+"</strong> &ndash; "+vitals.volunteernum[i][1]);
	if (i != vitals.volunteernum.length - 1)
	{
	   $volunteernum.append("<br />");
	}
    }

    // Fill in the classes num data
    $classnum = $j("#stats_classes > .module_group_body");
    $classnum.html('');
    for (var i = 0; i < vitals.classnum.length; i++)
    {
	$classnum.append("<strong>"+vitals.classnum[i][0]+"</strong> &ndash; "+vitals.classnum[i][1]);
	if (i != vitals.classnum.length - 1)
	{
	    $classnum.append("<br />");
	}
    }

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
    $hournum = $j("#stats_hours > .module_group_body");
    $hournum.html('');
    for (var i = 0; i < vitals.hournum.length; i++)
    {
	$hournum.append("<strong>"+vitals.hournum[i][0]+"</strong> &ndash; "+Math.round(100.0*vitals.hournum[i][1])/100.0);
	if (i != vitals.hournum.length - 1)
	{
	    $hournum.append("<br />");
	}
    }

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
    html_string = "<table><tr><th colspan='"+(shirtnum.sizes.length+1)+"'>Teacher T-Shirts</th></tr>";
    // Sizes header
    html_string = html_string.concat("<tr><td></td>");
    for (var i = 0; i < shirtnum.sizes.length; i++)
    {
	html_string = html_string.concat("<th class='smaller'>"+shirtnum.sizes[i]+"</th>");
    }
    html_string = html_string.concat("</tr>");
    // Types
    for (var i = 0; i < shirtnum.data.teachers.length; i++)
    {
	var curDist = shirtnum.data.teachers[i];
	//  console.log(curDist);
	html_string = html_string.concat("<tr><th class='smaller'>"+curDist.type+"</th>");
	for (var j = 0; j < curDist.distribution.length; j++)
	{
	    html_string = html_string.concat("<td>"+curDist.distribution[j]+"</td>");
	}
	html_string = html_string.concat("</tr>");
    }
    html_string = html_string.concat("</table>");
    $tshirts.html(html_string);
    
    //  Fill in the lunch/sibling discount table
    $splashinfo = $j("#stats_splashinfo > .module_group_body");
    if (splashinfo)
    {
        $splashinfo.html("<p><ul>    \
            <li>Saturday Lunch    \
                <ul id=\"splashinfo_lunchsat_list\">    \
                </ul>    \
            </li>    \
            <li>Sunday Lunch    \
                <ul id=\"splashinfo_lunchsun_list\">    \
                </ul>    \
            </li>    \
            <li>Sibling Discount    \
                <ul id=\"splashinfo_siblings_list\">    \
                </ul>    \
            </li>    \
            </ul>    \
            </p>");
        var splashinfo_keys = ["lunchsat", "lunchsun", "siblings"];
        for (var i = 0; i < splashinfo_keys.length; i++)
        {
            var ul_top = $j("#splashinfo_" + splashinfo_keys[i] + "_list");
            for (var key in splashinfo.data[splashinfo_keys[i]])
            {
                console.log(splashinfo_keys[i] + ": " + key + " -> " + splashinfo.data[splashinfo_keys[i]][key]);
                ul_top.append("<li><b>" + key + "</b>: " + splashinfo.data[splashinfo_keys[i]][key]);
            }
        }
    }
    else
        $splashinfo.html("SplashInfo module is not enabled -- no statistics");
    
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
