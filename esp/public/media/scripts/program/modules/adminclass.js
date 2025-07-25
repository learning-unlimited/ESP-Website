//  Global variables for storing the class and section data
var classes_global = {};

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

function show_saving_popup() {
  saving_popup
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
    return $j("<div/>")
        .append("<b>"+field+":</b>")
        .append($j("<div/>").text(content));
}

function getShortTitle(clsObj) {
    var shortTitle = clsObj.title;
    if (shortTitle.length > 60) {
        shortTitle = shortTitle.substring(0, 60);
        shortTitle = shortTitle.concat("...");
    }
    return shortTitle;
}

function fill_status_row(clsid, classes_data) {
  var class_info = classes_data.classes[clsid];
  // Get the status from our local data in case we've changed it
  var status_details = getStatusDetails(classes_global[clsid].status);
  var status_string = status_details['text'];

  var sections_table = $j('<table>').css("width", "100%")
  sections_table.append(
    $j("<tr/>").append(
        $j("<th/>"),
        $j("<th class='smaller'>Time</th>"),
        $j("<th class='smaller'>Room</th>"),
        $j("<th class='smaller'>Priority</th>"),
        $j("<th class='smaller'>Interested</th>"),
        $j("<th class='smaller'>Enrolled</th>")
    )
  );
  for (var i = 0; i < class_info.sections.length; i++)
  {
    var sec = class_info.sections[i];
    var sec_row = $j("<tr/>")
    sec_row.append($j("<td>" + (i + 1) + "</td>"))
    if (sec.time.length > 0) {
        sec_row.append($j("<td>" + sec.time + "</td>"))
        sec_row.append($j("<td>" + sec.room + "</td>"))
    }
    else {
        sec_row.append($j("<td colspan='2'>not scheduled</td>"))
    }
    sec_row.append($j("<td>" + sec.num_students_priority + "</td>"))
    sec_row.append($j("<td>" + sec.num_students_interested + "</td>"))
    sec_row.append($j("<td>" + sec.num_students_enrolled + "</td>"))
    sections_table.append(sec_row)
  }
  
  if (class_info.is_scheduled) {
    var buttons = [
    {
      text: "Approve (all sections)",
      cls: ["btn", "btn-success"],
      click: function() {
        update_class(clsid, 10);
      }
    },
    {
      text: "Unreview",
      cls: ["btn", "btn-inverse"],
      click: function() {
        update_class(clsid, 0);
      }
    },
    {
      text: "Cancel on class management page",
      cls: ["btn", "btn-warning"],
      click: function() {
        window.open("/manage/"+base_url+"/manageclass/"+clsid);
      }
    }]
  } else {
    var buttons = [
    {
      text: "Approve (all sections)",
      cls: ["btn", "btn-success"],
      click: function() {
        update_class(clsid, 10);
      }
    },
    {
      text: "Unreview",
      cls: ["btn", "btn-inverse"],
      click: function() {
        update_class(clsid, 0);
      }
    },
    {
      text: "Reject (all sections)",
      cls: ["btn", "btn-warning"],
      click: function() {
        update_class(clsid, -10);
      }
    }]
  }
  var button_els = buttons.map((item) => $j("<button/>").text(item.text).addClass(item.cls).on("click", item.click))
  
  var vitals_div = $j("<div/>")
    .css("justify-content", "space-around")
    .append(make_attrib_para("Max Size", class_info.class_size_max).css("text-align", "center"))
    .append(make_attrib_para("Duration", class_info.duration).css("text-align", "center"))
    .append(make_attrib_para("Grade Range", class_info.grade_range).css("text-align", "center"))
    .append(make_attrib_para("Category", class_info.category).css("text-align", "center"));
  if (class_info.class_style) vitals_div.append(make_attrib_para("Style", class_info.class_style).css("text-align", "center"));
  if (class_info.difficulty) vitals_div.append(make_attrib_para("Difficulty", class_info.difficulty).css("text-align", "center"));
  if (class_info.prereqs) vitals_div.append(make_attrib_para("Prereqs", class_info.prereqs).css("text-align", "center"));

  sections_table
    .css("min-width", "max(200px, 40%)")
    .css("flex", "1 1 0px");
  var desc_div = make_attrib_para("Description", class_info.class_info)
    .css("min-width", "max(200px, 40%)")
    .css("flex", "1 1 0px");

  var status_wrapper = $j("#status_wrapper");
  status_wrapper
    .html('')
    .attr('clsid', clsid)
    .append(vitals_div)
    .append(
      $j("<div/>")
        .css("padding-top", "10px")
        .css("padding-left", "10px")
        .css("padding-right", "10px")
        .append(desc_div)
        .append(sections_table)
    );
  
  if (class_info.special_requests || class_info.purchases || class_info.comments) {
      var comments_div = $j("<div/>").css("padding-top", "10px").css("justify-content", "space-around");
      if (class_info.special_requests) comments_div.append(make_attrib_para("Requests", class_info.special_requests));
      if (class_info.purchases) comments_div.append(make_attrib_para("Planned Purchases", class_info.purchases));
      if (class_info.comments) comments_div.append(make_attrib_para("Comments", class_info.comments));
      status_wrapper.append(comments_div);
  }
  status_wrapper.append(
    $j("<div/>")
      .css("padding-top", "10px")
      .css("justify-content", "center")
      .append(button_els));
}

function show_status_row(clsid) {
  var status_row = $j("#status_row");
  if (status_row.length > 0) {
      var status_id = status_row.data("cls");
      status_row.remove();
      if (status_id == clsid) {
          return false;
      }
  }
  var $target = $j("#" + clsid);
  // Show an intermediate screen while we load class data
  $target.after(createClassStatusRow(clsid));
  
  // Load the class data and fill the new row using it
  json_get('class_admin_info', {'class_id': clsid},
    function(data) {
      fill_status_row(clsid, data);
    },
    function(jqXHR, status, errorThrown) {
      if (errorThrown == "NOT FOUND") {
        $j("#status_wrapper")
          .html("Error: JSON view not found. Possible fix: Enable the JSON Data Module.");
      }
    }
  );
}

function createClassStatusRow(clsid) {
    var tr = $j(document.createElement('tr'));
    tr.data("cls", clsid);
    tr.attr("id", "status_row");
    var td = $j(document.createElement('td'));
    td.attr("colspan", has_moderator_module === "True" ? 6 : 5);
    td.append($j("<div/>").attr("id", "status_wrapper").html('Loading class info...'));
    tr.append(td);

    // Return the jQuery node
    return tr;
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
      // Update our local data
      classes_global[clsid].status = statusId;

      // Set the appropriate styling and tag text
      var el = $j("#" + clsid).find("td.classname > span");
      el.removeClass("unapproved").removeClass("approved").removeClass("dashboard_blue").removeClass("dashboard_red");

      for(var i = 0; i < status_details['classes'].length; ++i)
      {
        el.addClass(status_details['classes'][i]);
      }

      el.find("strong").text('[' + status_details['text'] + ']');
      
      // Close the dialog box
      saving_popup.dialog("close");
    }
  });
}

function fillClasses(data)
{
    // First pull out the data
    var classes = data.classes;

    // Clear the current classes list (most likely just "Loading...")
    $j("#classes_anchor").html('');

    // Now loop through and render each class row
    for (var i in classes) {
        var cls = classes[i];
        $j("#classes_anchor").append(createClassRow(cls));
    }

    //  Save the data for later if we need it
    classes_global = classes;
}

function createClassIdTd(clsObj) {
    return $j('<td/>', {
      'class': 'clsleft classname',
      'style': 'text-align: center;',
      'title': clsObj.emailcode,
    }).append(
        $j('<strong/>').text(clsObj.emailcode)
    ).attr("data-st-key", clsObj.id);
}

function createClassTitleTd(clsObj) {
    var status_details = getStatusDetails(clsObj.status);
    var title_css_class = status_details.classes.join(" ");
    return $j('<td/>', {
      'class': 'clsleft classname',
      'style': 'word-wrap: break-word; max-width: 35%;',
      'title': clsObj.title,
    }).append(
        $j('<span/>', {'class': title_css_class})
            .text(clsObj.title)
    ).attr("data-st-key", clsObj.title);
}

function createClassStatusTd(clsObj) {
    var status_details = getStatusDetails(clsObj.status);
    var title_css_class = status_details.classes.join(" ");
    var clsStatus = status_details.text;
    var statusStrong = $j('<strong/>').text('[' + clsStatus + ']');
    return $j('<td/>', {
      'class': 'clsleft classname no_mobile',
      'title': clsStatus,
    }).append(
        $j('<span/>', {'class': title_css_class})
            .append(statusStrong)
    ).attr("data-st-key", clsObj.clsStatus);
}

function createTeacherListTd(clsObj) {
    var td = $j('<td/>', {
        'class': 'clsleft classname',
        'style': 'font-style: italic',
        'title': 'Teacher names',
    });
    $j.each(clsObj.teachers, function(index, val) {
        if (index) {
            td.append(', ');
        }
        var teacher = json_data.teachers[val];
        var href = '/manage/userview?username=' + teacher.username + '&program=' + program_id;
        td.append($j('<a/>', {href: href}).text(
            teacher.first_name + ' ' + teacher.last_name));
    });
    return td;
}

function createModeratorListTd(clsObj) {
    var td = $j('<td/>', {
        'class': 'clsleft classname',
        'style': 'font-style: italic',
        'title': moderator_title + ' names',
    });
    $j.each(clsObj.moderators, function(index, val) {
        if (index) {
            td.append(', ');
        }
        var moderator = json_data.moderators[val];
        var href = '/manage/userview?username=' + moderator.username + '&program=' + program_id;
        td.append($j('<a/>', {href: href}).text(
            moderator.first_name + ' ' + moderator.last_name));
    });
    return td;
}

function createDeleteButtonTd(clsObj) {
    var action = '/manage/' + base_url + '/deleteclass/' + clsObj.id;
    return $j("<div/>", {'class': 'clsmiddle'}).append(
        $j("<form/>", {
            'method': 'post',
            'action': action,
            'onsubmit': 'return deleteClass();',
        }).append(
            $j("<input/>", {
                'class': 'btn btn-inverse',
                'type': 'submit',
                'value': 'Delete',
            })
        )
    );
}

function createLinkButtonTd(clsObj, type, verb) {
    var href = '/manage/' + base_url + '/' + type + '/' + clsObj.id;
    return $j("<div/>", {'class': 'clsmiddle'}).append(
        $j("<a/>", {
            'href': href,
            'title': verb + ' ' + getShortTitle(clsObj),
            'class': 'btn',
            'style': 'white-space: nowrap;',
        }).text(verb)
    );
}
function createStatusButtonTd(clsObj) {
    var clickjs = ('show_status_row(' + clsObj.id + '); return false;');

    return $j("<div/>", {'class': 'clsmiddle'}).append(
        $j("<a/>", {
            'href': '#',
            'title': 'Set the status of ' + getShortTitle(clsObj),
            'class': 'btn',
            'style': 'white-space: nowrap;',
            'onclick': clickjs,
        }).text('Status')
    );
}

function createButtonTd(clsObj)
{
    return $j("<td/>", {'class': 'button_td'}).append(
        createDeleteButtonTd(clsObj),
        createLinkButtonTd(clsObj, 'editclass', 'Edit'),
        createLinkButtonTd(clsObj, 'manageclass', 'Manage'),
        createStatusButtonTd(clsObj)
    );
}

function createClassRow(clsObj)
{
    var tr = $j(document.createElement('tr'));
    tr.attr("id", clsObj.id);
    tr.append(
        createClassIdTd(clsObj),
        createClassTitleTd(clsObj),
        createClassStatusTd(clsObj),
        createTeacherListTd(clsObj),
    );
    if (has_moderator_module === "True") {
        tr.append(createModeratorListTd(clsObj));
    }
    tr.append(createButtonTd(clsObj));

    // Add in the CSRF onsubmit checker
    tr.find("form[method=post]").on("submit", function() { return check_csrf_cookie(this); });

    // Return the jQuery node
    return tr;
}

function handle_sort_control()
{
    //  Detect specified sorting method
    var method = $j("#dashboard_sort_control").prop("value");
    //  Update the sorttable_customkey of the first td in each row
    $j("#classes_anchor > tr").each(function (index) {
        var clsid = parseInt($j(this).attr("id"))
        if (!classes_global.hasOwnProperty(clsid)) {
            console.log("No class found with ID: " + clsid);
            return;
        }
        var cls = classes_global[clsid];
        if (method == "id")
            $j(this).children("td").first().attr("data-st-key", cls.id);
        else if (method == "category")
            $j(this).children("td").first().attr("data-st-key", cls.emailcode);
        else if (method == "size")
            $j(this).children("td").first().attr("data-st-key", cls.class_size_max);
    });
    
    $j("#header-row > th").first().removeClass("sorttable_sorted sorttable_sorted_reverse");
    //  sorttable.makeSortable($j("#dashboard_class_table").get(0));
    if (sorttable.innerSortFunction)
        sorttable.innerSortFunction.apply($j("#header-row > th").get(0), []);
}

function setup_sort_control()
{
    $j("#dashboard_sort_control").on("change", handle_sort_control);
    handle_sort_control();
    
    // whenever table is sorted, remove any status row(s)
    $j('#dashboard_class_table')[0].addEventListener('sorttable.sorted', (e) => $j("#status_row").remove());
}
