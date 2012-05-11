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
      status_string = "Accepted but hidden";
      break;
    case 10:
      status_string = "Accepted";
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
        },
      },
      {
        text: "Unreview",
        click: function() {
          unreview_class($j(this).attr('clsid'));
        },
      },
      {
        text: "Reject (all sections)",
        click: function() {
          reject_class($j(this).attr('clsid'));
        },
      }])
    .html('')
    .append("<p><b>Status:</b> " + status_string + "</p>")
    .append("<p><b>Sections:</b> " + class_info.sections.length + "</p>")
    .append("<p><b>Max Size:</b> " + class_info.class_size_max + "</p>")
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
    url: "/manage/{{ program.url }}/reviewClass",
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

  // Set the appropriate styling
  $j("#"+clsid+"-row").find(".unapproved")
      .removeClass("unapproved")
      .addClass("approved");
}

function unreview_class(clsid) {
  // Show a popup while saving to avoid a "laggy" feeling
  show_saving_popup();

  // Make the AJAX request to actually set the class status
  $j.ajax({
    url: "/manage/{{ program.url }}/reviewClass",
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

  // Set the appropriate styling
  $j("#"+clsid+"-row").find(".approved")
      .removeClass("approved")
      .addClass("unapproved");
}

function reject_class(clsid) {
  // Show a popup while saving to avoid a "laggy" feeling
  show_saving_popup();

  // Make the AJAX request to actually set the class status
  $j.ajax({
    url: "/manage/{{ program.url }}/reviewClass",
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

  // Set the appropriate styling
  $j("#"+clsid+"-row").find(".approved")
      .removeClass("approved")
      .addClass("unapproved");
}

function fillClasses(data)
{
    // First assemble the classes associative array
    sections = data.sections;
    classes = {};
    for (var i in sections)
    {
	var section = sections[i];
	if (section.parent_class in classes)
	{
	    classes[section.parent_class].sections.push(section);
	}
	else
	{
	    classes[section.parent_class] = {
		id: section.parent_class,
		sections: [section],
	    };
	}
    }

    // Clear the current classes list (most likely just "Loading...")
    $j("#classes_anchor").html('');

    // Now loop through and render each class row
    for (var i in classes)
    {
	var cls = classes[i];
	$j("#classes_anchor").append(createClassRow(cls));
    }
}

function createClassRow(clsObj)
{
    var template = " \
    <tr> \
    <td class='clsleft classname'> \
      <span title='{{ cls.title }}'> \
        <strong>{{ cls.emailcode }}.</strong> \
        <span {{ title_class }}>{{ cls.title }}</span> \
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
       <form method='post' action='/manage/{{ program.getUrlBase }}/deleteclass/{{ cls.id }}' onsubmit=;return deleteClass();'> \
         <input class='button' type='submit' value='Delete' /> \
       </form> \
    </td> \
    <td class='clsmiddle'> \
       <form method='post' action='/teach/{{ program.url }}/editclass/{{ cls.id }}'> \
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
    <td class='clsmiddle rapid_approval_button' style='display:none'> \
      <a href='#' title='Set the status of {{ cls.title }}' class='abutton' style='white-space: nowrap;' onclick='show_approve_class_popup({{ cls.id }}); return false;'> \
	Status \
      </a> \
    </td> \
    </tr> \
";

    // Now fill in the values in the template
    console.log("Filling with clsObj:");
    console.log(clsObj);
    teacher_list = clsObj.sections[0].teachers;
    console.log("Teacher_list:");
    console.log(teacher_list);
    teacher_list = $j.map(teacher_list, function(val, index) {
	console.log("Looking for teacher: " + val);
	return json_data.teachers[val].first_name + " " + json_data.teachers[val].last_name;
    });
    teacher_list_string = "( " + teacher_list.join(", ") + " )";

    template = template.replace(new RegExp("{{ cls.id }}", "g"), clsObj.id)
	.replace(new RegExp("{{ cls.title }}", "g"), clsObj.sections[0].title)
	.replace(new RegExp("{{ cls.emailcode }}", "g"), clsObj.sections[0].emailcode)
	.replace(new RegExp("{{ teacher_names }}", "g"), teacher_list_string);
    // Return a jQuery node of the template
    return $j(template);
}