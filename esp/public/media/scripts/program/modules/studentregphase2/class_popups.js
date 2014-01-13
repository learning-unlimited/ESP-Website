
// The class description popup is a global variable, because we only want
// one object, and we don't want to recreate it each time
var class_desc_popup;
// Function to initially create the class description popup (using jQuery UI dialogs)
create_class_info_dialog = function(){
    class_desc_popup = $j('<div></div>').dialog({
	    autoOpen: false,
	    minWidth: 400,
	    minHeight: 300,
	    modal: true,
	    buttons: {
		Ok: function() {
		    $j(this).dialog("close");
		}
	    },
	    title: ''
	});
};

// Dictionary to keep track of classes' extra info as and when we load them
var class_info = {};
// Initial popup that tells the user we're loading the class data
loading_class_desc = function(){
    class_desc_popup.dialog('option', 'title', 'Loading');
    class_desc_popup.dialog('option', 'width', 400);
    class_desc_popup.dialog('option', 'height', 200);
    class_desc_popup.dialog('option', 'position', 'center');
    class_desc_popup.html('Loading class info...');
    class_desc_popup.dialog('open');
};


// Function to fill the class description popup
fill_class_desc = function(class_id){
    var parent_class_id = sections[class_id].parent_class;
    extra_info = class_info[parent_class_id];
    class_desc_popup.dialog('option', 'title', sections[class_id].emailcode + ": " + extra_info.title);
    class_desc_popup.dialog('option', 'width', 600);
    class_desc_popup.dialog('option', 'height', 400);
    class_desc_popup.dialog('option', 'position', 'center');
    class_desc_popup.html('');
    class_desc_popup.append("<p><b>Category:</b> " + extra_info.category + "</p>");
    //class_desc_popup.append("<p>Difficulty: " + extra_info.difficulty + "</p>");
    class_desc_popup.append("<p><b>Description:</b> " + extra_info.class_info + "</p>");
};


// Called to open a class description
open_class_desc = function(class_id){
    // Display a loading popup while we wait
    loading_class_desc();

    // Get the class info if we don't have it already
    var parent_class_id = sections[class_id].parent_class;
    if (!class_info[parent_class_id]){
	json_get('class_info', {'class_id': parent_class_id}, function(data){
		// Once we get the class data, store it for later, then go
		// fill the popup
		class_info[parent_class_id] = data.classes[parent_class_id];
		fill_class_desc(class_id);
	    });
    }
    else{
	// If we already have the data, go fill the popup
	fill_class_desc(class_id);
    }
};

