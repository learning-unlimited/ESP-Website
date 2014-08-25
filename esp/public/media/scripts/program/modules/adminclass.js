//  Global variables for storing the class and section data
var classes_global = {};
var sections_global = {};

function deleteClass() {
    if (confirm('Are you sure you would like to delete this class? \n Since you are an admin, you can delete this class with students. \n Deleting is hard to undo, so consider instead marking it unreviewed or rejected.')) {
       return true;
    }
    return false;
}
function assignRoom(clsid){
    form = document.getElementById('assignroom-'+clsid)
    form.submit();
}

var handleSubmit = function () { this.submit(); }
var handleCancel = function () { this.cancel(); }

function show_loading_class_popup() {
  class_desc_popup
    .dialog('option', 'title', 'Loading')
    .dialog('option', 'width', 400)
    .dialog('option', 'height', 200)
    .dialog('option', 'position', 'center')
    .dialog('option', 'buttons', [])
    .html('Loading class info...')
    .dialog('open');
}

function show_saving_popup() {
  class_desc_popup
    .dialog('option', 'title', 'Saving')
    .html('Saving the class status...')
    .dialog('option', 'buttons', [])
    .dialog('open');
}

//returns details (status string, action, and CSS classes) for a given status code
function getStatusDetails(statusCode) {
  if(statusCode == -20)
    return {text: "Cancelled", action: "", classes: ['unapproved', 'dashboard_red']};
  else if(statusCode == -10)
    return {text: "Rejected", action: "REJECT", classes: ['unapproved', 'dashboard_red']};
  else if(statusCode == 0)
    return {text: "Unreviewed", action: "UNREVIEW", classes: ['unapproved', 'dashboard_blue']};
  else if(statusCode == 5)
    return {text: "Approved but hidden", action: "", classes: ['approved']};
  else if(statusCode > 0)
    return {text: "Approved", action: "ACCEPT", classes: ['approved']};
  else //statusCode < 0
    return {text: "Unapproved", action: "", classes: ['unapproved']};
}

function make_attrib_para(field, content) {
    return $j("<p></p>")
        .append("<b>"+field+":</b>")
        .append($j("<div/>").text(content));
}

function fill_class_popup(clsid, classes_data) {
  var class_info = classes_data.classes[clsid];
  var status_details = getStatusDetails(class_info.status);
  var status_string = status_details['text'];

  var sections_list = $j('<ul>')
  for (var i = 0; i < class_info.sections.length; i++)
  {
    var sec = class_info.sections[i];
    if (sec.time.length > 0)
        sections_list.append($j('<li>').html(sec.time + " in " + sec.room + ": " + sec.num_students_priority + " priority, " + sec.num_students_interested + " interested, " + sec.num_students_enrolled + " enrolled"));
    else
        sections_list.append($j('<li>').html('Section ' + (i + 1) + ': not scheduled'));
  }

  class_desc_popup
    .dialog('option', 'title', class_info.emailcode + ": " +class_info.title)
    .dialog('option', 'width', 600)
    .dialog('option', 'height', 400)
    .dialog('option', 'position', 'center')
    .dialog('option', 'buttons', [
      {
        text: "Approve (all sections)",
        click: function() {
          update_class($j(this).attr('clsid'), 10);
        }
      },
      {
        text: "Unreview",
        click: function() {
          update_class($j(this).attr('clsid'), 0);
        }
      },
      {
        text: "Reject (all sections)",
        click: function() {
          update_class($j(this).attr('clsid'), -10);
        }
      }])
    .html('')
    .append(make_attrib_para("Status", status_string))
    .append(make_attrib_para("Teachers", class_info.teacher_names))
    .append(make_attrib_para("Sections", class_info.sections.length))
    .append(sections_list)
    .append(make_attrib_para("Max Size", class_info.class_size_max))
    .append(make_attrib_para("Duration", class_info.duration))
    .append(make_attrib_para("Location", class_info.location))
    .append(make_attrib_para("Grade Range", class_info.grade_range))
    .append(make_attrib_para("Category", class_info.category))
    //.append("<p>Difficulty: " + class_info.difficulty))
    .append(make_attrib_para("Prereqs", class_info.prereqs))
    // Ensure the class description gets HTML-escaped
    .append(make_attrib_para("Description", class_info.class_info))
    .append(make_attrib_para("Requests", class_info.special_requests))
    .append(make_attrib_para("Planned Purchases", class_info.purchases))
    .append(make_attrib_para("Comments", class_info.comments))
    .attr('clsid', clsid);
}

function show_approve_class_popup(clsid) {
  // Show an intermediate screen while we load class data
  show_loading_class_popup();

  // Load the class data and fill the popup using it
    json_get('class_admin_info', {'class_id': clsid},
    function(data) {
	fill_class_popup(clsid, data);
    },
    function(jqXHR, status, errorThrown) {
      if (errorThrown == "NOT FOUND") {
        class_desc_popup.dialog('option', 'title', 'Error');
        class_desc_popup.html("Error: JSON view not found.<br/>Possible fix: Enable the JSON Data Module.");
        class_desc_popup.dialog('option', 'buttons', [{
          text: "Ok",
          click: function() {
            $j(this).dialog("close");
          }
        }]);
      }
    });

}

// status should be the status integer
// this is one of {10 for ACCEPT, 0 for UNREVIEW, -10 for REJECT}
function update_class(clsid, statusId) {
  // Show a popup while saving to avoid a "laggy" feeling
  show_saving_popup();

  var status_details = getStatusDetails(statusId);

  // Make the AJAX request to actually set the class status
  $j.ajax({
    url: "/manage/"+base_url+"/reviewClass",
    type: "post",
    data: {
      class_id: clsid,
      review_status: status_details['action'],
      csrfmiddlewaretoken: csrf_token()
    },
    complete: function() {
      class_desc_popup.dialog("close");
    }
  });

  // Update our local data
  classes[clsid].status = statusId;

  // Set the appropriate styling and tag text
  var el = $j("#clsid-"+clsid+"-row").find("td > span > span");
  el.removeClass("unapproved").removeClass("approved").removeClass("dashboard_blue").removeClass("dashboard_red");

  for(var i = 0; i < status_details['classes'].length; ++i)
  {
    el.addClass(status_details['classes'][i]);
  }

  el.find("strong").text('[' + status_details['text'] + ']');
}

function fillClasses(data)
{
    // First pull out the data
    sections = data.sections;
    classes = data.classes;

    // Clear the current classes list (most likely just "Loading...")
    $j("#classes_anchor").html('');

    // Now loop through and render each class row
    for (var i in classes)
    {
	var cls = classes[i];
	$j("#classes_anchor").append(createClassRow(cls));
    }
    
    //  Save the data for later if we need it
    classes_global = classes;
    sections_global = sections;
}

function createClassRow(clsObj)
{
    var template = " \
    <tr id='clsid-{{ cls.id }}-row'> \
    <td class='clsleft classname'> \
      <span title='{{ cls.title }}'> \
        <strong>{{ cls.emailcode }}.</strong> \
        <span class='{{ title_css_class }}'>{{ cls.title }} \
        <strong>[{{ cls_status }}]</strong></span> \
      </span> \
    </td> \
    <td class='clsmiddle' style='font-size: 12px' width='40px'> \
      <span title='Control the enrollment of the class's sections'> \
      {{ section_links }} \
      </span> \
    </td> \
    <td class='clsleft classname' style='font-style: italic'> \
      <span title='Teacher Names'> \
        {{ teacher_names }} \
      </span> \
    </td> \
 \
 \
    <td class='clsmiddle'> \
       <form method='post' action='/manage/{{ program.getUrlBase }}/deleteclass/{{ cls.id }}' onsubmit='return deleteClass();'> \
         <input class='button' type='submit' value='Delete' /> \
       </form> \
    </td> \
    <td class='clsmiddle'> \
      <a href='/manage/{{ program.getUrlBase }}/editclass/{{ cls.id }}' title='Edit {{ cls.title }}' \
       class='abutton' style='white-space: nowrap;'> \
        Edit \
      </a> \
    </td> \
    <td class='clsmiddle'> \
      <a href='/manage/{{ program.getUrlBase }}/manageclass/{{ cls.id }}' title='Manage {{ cls.title }}' \
       class='abutton' style='white-space: nowrap;'> \
        Manage \
      </a> \
    </td> \
    <td class='clsmiddle rapid_approval_button'> \
      <a href='#' title='Set the status of {{ cls.title }}' class='abutton' style='white-space: nowrap;' onclick='show_approve_class_popup({{ cls.id }}); return false;'> \
	Status \
      </a> \
    </td> \
    </tr> \
";

    // Now fill in the values in the template
    var teacher_list = clsObj.teachers;
    teacher_list = $j.map(teacher_list, function(val, index) {
	return json_data.teachers[val].first_name + " " + json_data.teachers[val].last_name;
    });
    var teacher_list_string = teacher_list.join(", ");

    var section_link_list = "";
    for (var i = 0; i < clsObj.sections.length; i++)
    {
	var section = sections[clsObj.sections[i]];
	section_link_list = section_link_list.concat("<a href='/teach/"+base_url+"/select_students/"+section.id+"'>Sec. "+section.index+"</a><br />");
    }
    
    var class_title_trimmed = clsObj.title;
    if (class_title_trimmed.length > 40)
    {
	class_title_trimmed = class_title_trimmed.substring(0, 40);
	class_title_trimmed = class_title_trimmed.concat("...");
    }

    var status_details = getStatusDetails(clsObj.status);

    template = template.replace(new RegExp("{{ cls.id }}", "g"), clsObj.id)
	.replace(new RegExp("{{ cls.title }}", "g"), class_title_trimmed)
	.replace(new RegExp("{{ cls.emailcode }}", "g"), clsObj.emailcode)
	.replace(new RegExp("{{ teacher_names }}", "g"), teacher_list_string)
	.replace(new RegExp("{{ section_links }}", "g"), section_link_list)
	.replace(new RegExp("{{ program.getUrlBase }}", "g"), base_url)
	.replace(new RegExp("{{ title_css_class }}", "g"), status_details.classes.join(" "))
	.replace(new RegExp("{{ cls_status }}", "g"), status_details['text']);

    // Turn the template into a jQuery node
    $node = $j(template);

    // Add in the CSRF onsubmit checker
    $node.find("form[method=post]").submit(function() { return check_csrf_cookie(this); });

    // Return the jQuery node
    return $node;
}

function handle_sort_control()
{
    //  Detect specified sorting method
    var method = $j("#dashboard_sort_control").prop("value");
    //  Update the sorttable_customkey of the first td in each row
    $j("#classes_anchor > tr").each(function (index) {
        var clsid = parseInt($j(this).prop("id").split("-")[1])
        if (!classes_global.hasOwnProperty(clsid))
            return;
        var cls = classes_global[clsid];
        if (method == "id")
            $j(this).children("td").first().attr("sorttable_customkey", cls.id);
        else if (method == "category")
            $j(this).children("td").first().attr("sorttable_customkey", cls.emailcode);
        else if (method == "name")
            $j(this).children("td").first().attr("sorttable_customkey", cls.title);
        else if (method == "status")
            $j(this).children("td").first().attr("sorttable_customkey", cls.status);
        else if (method == "size")
            $j(this).children("td").first().attr("sorttable_customkey", cls.class_size_max);
        else if (method == "special")
            $j(this).children("td").first().attr("sorttable_customkey", (cls.message_for_directors || "").length + (cls.requested_special_resources || "").length);
    });
    
    $j("#header-row > th").first().removeClass("sorttable_sorted sorttable_sorted_reverse");
    //  sorttable.makeSortable($j("#dashboard_class_table").get(0));
    if (sorttable.innerSortFunction)
        sorttable.innerSortFunction.apply($j("#header-row > th").get(0), []);
}

function setup_sort_control()
{
    $j("#dashboard_sort_control").change(handle_sort_control);
    handle_sort_control();
}
