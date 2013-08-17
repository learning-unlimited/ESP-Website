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

function fill_class_popup(clsid, classes_data) {
  var class_info = classes_data.classes[clsid];
  var status_string;
  switch(class_info.status)
  {
    case -20:
      status_string = "Cancelled";
      break;
    case -10:
      status_string = "Rejected";
      break;
    case 0:
      status_string = "Unreviewed";
      break;
    case 5:
      status_string = "Approved but hidden";
      break;
    case 10:
      status_string = "Approved";
      break;
  }

  class_desc_popup
    .dialog('option', 'title', class_info.title)
    .dialog('option', 'width', 600)
    .dialog('option', 'height', 400)
    .dialog('option', 'position', 'center')
    .dialog('option', 'buttons', [
      {
        text: "Approve (all sections)",
        click: function() {
          approve_class($j(this).attr('clsid'));
        }
      },
      {
        text: "Unreview",
        click: function() {
          unreview_class($j(this).attr('clsid'));
        }
      },
      {
        text: "Reject (all sections)",
        click: function() {
          reject_class($j(this).attr('clsid'));
        }
      }])
    .html('')
    .append("<p><b>Status:</b> " + status_string + "</p>")
    .append("<p><b>Sections:</b> " + class_info.sections.length + "</p>")
    .append("<p><b>Max Size:</b> " + class_info.class_size_max + "</p>")
    .append("<p><b>Duration:</b> " + class_info.duration + "</p>")
    .append("<p><b>Grade Range:</b> " + class_info.grade_range + "</p>")
    .append("<p><b>Category:</b> " + class_info.category + "</p>")
    //.append("<p>Difficulty: " + class_info.difficulty + "</p>")
    .append("<p><b>Prereqs:</b> " + class_info.prereqs + "</p>")
    .append("<p><b>Description:</b> " + class_info.class_info + "</p>")
    .attr('clsid', clsid);
}

function show_approve_class_popup(clsid) {
  // Show an intermediate screen while we load class data
  show_loading_class_popup();

  // Load the class data and fill the popup using it
  json_get('class_info', {'class_id': clsid},
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

function approve_class(clsid) {
  // Show a popup while saving to avoid a "laggy" feeling
  show_saving_popup();

  // Make the AJAX request to actually set the class status
  $j.ajax({
    url: "/manage/"+base_url+"/reviewClass",
    type: "post",
    data: {
      class_id: clsid,
      review_status: "ACCEPT",
      csrfmiddlewaretoken: csrf_token()
    },
    complete: function() {
      class_desc_popup.dialog("close");
    }
  });

  // Update our local data
  classes[clsid].status = 10;

  // Set the appropriate styling
  $j("#clsid-"+clsid+"-row").find("td > span > span")
	.removeClass("unapproved").removeClass("dashboard_blue").removeClass("dashboard_red")
	.addClass("approved");
}

function unreview_class(clsid) {
  // Show a popup while saving to avoid a "laggy" feeling
  show_saving_popup();

  // Make the AJAX request to actually set the class status
  $j.ajax({
    url: "/manage/"+base_url+"/reviewClass",
    type: "post",
    data: {
      class_id: clsid,
      review_status: "UNREVIEW",
      csrfmiddlewaretoken: csrf_token()
    },
    complete: function() {
      class_desc_popup.dialog("close");
    }
  });

  // Update our local data
  classes[clsid].status = 0;

  // Set the appropriate styling
  $j("#clsid-"+clsid+"-row").find("td > span > span")
	.removeClass("approved").removeClass("dashboard_red")
	.addClass("unapproved").addClass("dashboard_blue");
}

function reject_class(clsid) {
  // Show a popup while saving to avoid a "laggy" feeling
  show_saving_popup();

  // Make the AJAX request to actually set the class status
  $j.ajax({
    url: "/manage/"+base_url+"/reviewClass",
    type: "post",
    data: {
      class_id: clsid,
      review_status: "REJECT",
      csrfmiddlewaretoken: csrf_token()
    },
    complete: function() {
      class_desc_popup.dialog("close");
    }
  });  

  // Update our local data
  classes[clsid].status = -10;

  // Set the appropriate styling
  $j("#clsid-"+clsid+"-row").find("td > span > span")
	.removeClass("approved").removeClass("dashboard_blue")
	.addClass("unapproved").addClass("dashboard_red");
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
    <td class='clsleft classname' style='font-size: 60%; font-style: italic;'> \
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
       <form method='post' action='/teach/{{ program.getUrlBase }}/editclass/{{ cls.id }}'> \
         <input type='hidden' name='command' value='edit_class_{{ cls.id }}'> \
         <input type='hidden' name='manage' value='manage'> \
         <input class='button' type='submit' value='Edit'> \
       </form> \
    </td> \
    <td class='clsmiddle'> \
      <a href='/manage/{{ program.getUrlBase }}/manageclass/{{ cls.id }}' title='Manage {{ cls.title }}' \
       class='abutton' style='white-space: nowrap;'> \
        Manage \
      </a> \
    </td> \
    <td class='clsmiddle rapid_approval_button' {{ rapid_approval_style }}> \
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
    var teacher_list_string = "( " + teacher_list.join(", ") + " )";

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


    var title_css_class = "";
    var cls_status = "";
    if (clsObj.status == 0)
    {
	title_css_class = "unapproved dashboard_blue";
	cls_status = "UNREVIEWED";
    }
    else if (clsObj.status == -10)
    {
	title_css_class = "unapproved dashboard_red";
	cls_status = "REJECTED";
    }
    else if (clsObj.status == -20)
    {
	title_css_class = "unapproved dashboard_red";
	cls_status = "CANCELLED";
    }
    else if (clsObj.status > 0)
    {
	title_css_class = "approved";
	cls_status = "APPROVED";
    }
    else if (clsObj.status <= 0)
    {
	title_css_class = "unapproved";
	cls_status = "UNAPPROVED";
    }

    var rapid_approval_style = "style='display:none;'";
    if (use_rapid_approval)
    {
	rapid_approval_style = "";
    }

    template = template.replace(new RegExp("{{ cls.id }}", "g"), clsObj.id)
	.replace(new RegExp("{{ cls.title }}", "g"), class_title_trimmed)
	.replace(new RegExp("{{ cls.emailcode }}", "g"), clsObj.emailcode)
	.replace(new RegExp("{{ teacher_names }}", "g"), teacher_list_string)
	.replace(new RegExp("{{ section_links }}", "g"), section_link_list)
	.replace(new RegExp("{{ program.getUrlBase }}", "g"), base_url)
	.replace(new RegExp("{{ title_css_class }}", "g"), title_css_class)
	.replace(new RegExp("{{ cls_status }}", "g"), cls_status)
	.replace(new RegExp("{{ rapid_approval_style }}", "g"), rapid_approval_style);

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
