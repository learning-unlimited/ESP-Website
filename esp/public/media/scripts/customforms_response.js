$j(document).ready(function() {
    //csrf stuff
	$j(document).ajaxSend(function(event, xhr, settings) {
	function getCookie(name) {
	    var cookieValue = null;
	    if (document.cookie && document.cookie != '') {
	        var cookies = document.cookie.split(';');
	        for (var i = 0; i < cookies.length; i++) {
	            var cookie = jQuery.trim(cookies[i]);
	            // Does this cookie string begin with the name we want?
	            if (cookie.substring(0, name.length + 1) == (name + '=')) {
	                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
	                break;
	            }
	        }
	    }
	    return cookieValue;
	}
	function sameOrigin(url) {
	    // url could be relative or scheme relative or absolute
	    var host = document.location.host; // host + port
	    var protocol = document.location.protocol;
	    var sr_origin = '//' + host;
	    var origin = protocol + sr_origin;
	    // Allow absolute or scheme relative URLs to same origin
	    return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
	        (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
	        // or any other URL that isn't scheme relative or absolute i.e relative.
	        !(/^(\/\/|http:|https:).*/.test(url));
	}
	function safeMethod(method) {
	    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
	}

	if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
	    xhr.setRequestHeader("X-CSRFToken", getCookie('esp_csrftoken'));
	}
    });
    //end of csrf stuff
    
    //Grabbing the form-id
    var form_id=$j('#form_id').val();
    //Getting response data
    $j.ajax({
	url:'/customforms/getData/',
	data:{'form_id':form_id},
	type:'GET',
	dataType:'json',
	async:false,
	success: function(form_data) {
	    createGrid(form_data);
	}
    });
});

//  Function to convert an uploaded file storage location to a URL.
function file_link_formatter(cellvalue, options, rowObject)
{
    var url_path = cellvalue.split("media/uploaded/")[1];
    if (url_path) {
        var url_dir = url_path.split("/");
        return "<a href=\"/media/uploaded/" + url_dir.slice(0, url_dir.length - 1).join("/") + "/" + encodeURIComponent(url_dir[url_dir.length - 1]) +  "\">" + url_dir[url_dir.length - 1] + "</a>";
    } else {
        return ""
    }
}

var createGrid=function(form_data){
    $j("#jqGrid").jqGrid({
	datatype: "local",
	height: 250,
	colNames: $j.map(form_data['questions'], function(val, index) {
	    return val[1];
	}),
	colModel: $j.map(form_data['questions'], function(val, index) {
	    var result = {name: val[0], index: val[0]};
        //  Substitute in custom formatter defined above in order to link to uploaded files.
        if (val[2] == "file")
        {
            result['formatter'] = file_link_formatter;
        }
        return result;
	}),
	caption: "Form responses",
	rowNum: 10,
	pager: "#jqGridPager"
    });
    $j("#jqGrid").jqGrid('navGrid', '#jqGridPager',
			{view: true, edit: false, add: false, del: false},
			{}, {}, {}, 
			{multipleSearch: true, closeOnEscape: true},
		        {closeOnEscape: true});
    $j.each(form_data['answers'], function(index, val) {
	delete val.id;
	$j("#jqGrid").jqGrid('addRowData', index+1, val);
    });
};

var copyObject=function(answers){
    //Copies the 'answers' array into another array
    ret_val=[];
    $j.each(answers, function(idx,el){
	ret_val.push({});
	$j.extend(ret_val[idx], el);
    });
    //return ret_val;
}
