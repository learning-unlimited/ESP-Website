dojo.addOnLoad(function() {
	
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
	        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
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
			console.log(form_data);
			createGrid(form_data);
		}
	});
});

var getStore=function(answers) {
	//Returns the ItemFileReadStore object for this grid
	console.log('in getStore');
    
    //  Join together segments of compound fields (perhaps they should be displayed as separate columns)
    for (var i = 0; i < answers.length; i++)
    {
        var item = answers[i];
        for (var key in item)
        {
            if (item[key] instanceof Array)
                answers[i][key] = item[key].join(" ");
        }
    }

	console.log(answers);
	var store=new dojo.data.ItemFileReadStore({data:{'items':answers}});
	console.log('out getStore');
	console.log(store);	
	return store;
};

var getLayout=function(data) {
	//Returns the layout for this grid
	console.log('in getLayout');
	var layout=[];
	$j.each(data, function(idx, val){
		layout.push({
			field:val[0],
			name:val[1],
			width:'80px',
			datatype:'string'
		});
	});
	console.log('out getLayout');
	console.log(layout);
	return layout;
};

var createGrid=function(form_data){
	//Created the data-grid
	console.log('in createGrid');
	console.log(form_data)
	var stor, layt, grid;
	layt=getLayout(form_data['questions']);
	stor=getStore(form_data['answers']);
	grid=new dojox.grid.EnhancedGrid({
		store:stor,
		clientSort:true,
		structure:layt,
		columnReordering:true,
		jsId:grid,
		rowSelector:'20px',
		loadingMessage:"Please wait while your data is fetched",
		plugins:{
			filter:true
		}
	},
	document.createElement('div'));
	
	dojo.byId("gridContainer").appendChild(grid.domNode);
	grid.startup();
	console.log('out createGrid');
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
