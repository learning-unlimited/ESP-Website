//Defining the master 'list' for form elements
var formElements={
	'Generic':{
		textField:{'disp_name':'Single Line Text - Short','ques':''},
		longTextField:{'disp_name':'Single Line Text - Long','ques':''},
		longAns:{'disp_name':'Long Answer','ques':''},
		reallyLongAns:{'disp_name':'Really Long Answer','ques':''},
		radio:{'disp_name':'Radio Button Group','ques':'Pick an option'},
		dropdown:{'disp_name':'Dropdown List','ques':'Pick an option'},
		multiselect:{'disp_name':'Multiple Select', 'ques':'Pick some options'},
		checkboxes:{'disp_name':'Checkbox Group', 'ques':'Pick some options'},
		numeric:{'disp_name':'Numeric Field','ques':''},
		date:{'disp_name':'Date','ques':'Date'},
		time:{'disp_name':'Time','ques':'Time'},
		file:{'disp_name':'File Upload','ques':'Upload file'},
		section:{'disp_name':'Section', 'ques':'Section'},
		page:{'disp_name':'Page', 'ques':'Page'}
	},
	'Personal':{
		name:{'disp_name':'Name','ques':'Your name'},
		gender:{'disp_name':'Gender','ques':'Gender'},
		phone:{'disp_name':'Phone no.','ques':'Phone no.'},
		email:{'disp_name':'Email','ques':'Email'},
		address:{'disp_name':'Address','ques':'Address'},
		state:{'disp_name':'State','ques':'State'},
		city:{'disp_name':'City','ques':'City'}
	}
};
var program_fields={'fields':{
	courses:{'disp_name':'Courses', 'ques':'Courses'}
}};
var elemTypes = {
	// Stores the available types of form objects, and their number in the form
	'textField':0,
	'longTextField':0,
	'longAns':0,
	'reallyLongAns':0,
	'radio':0,
	'dropdown':0,
	'multiselect':0,
	'checkboxes':0,
	'numeric':0,
	'date':0,
	'time':0,
	'file':0,
	'name':0,
	'gender':0,
	'phone':0,
	'email':0,
	'address':0,
	'state':0,
	'city':0,
	'courses':0
};

var covenience = {
	//A list of convenience methods
	
};

var currElemType, currElemIndex, optionCount=1, formTitle="Form",currCategory='',$prevField, $currField, secCount=1, $currSection, pageCount=1, $currPage;

$(document).ready(function() {
    $('#button_add').click(function(){insertField($('#elem_selector').attr('value'),$prevField)});
	$('#submit').click(submit);
	$('#button_title').click(updateTitle);
	$('#input_form_title').bind('change', updateTitle);
	$('#input_form_description').bind('change', updateDesc);
	
	$currSection=$('#section_0');
	$currPage=$('#page_0');
	//'Initializing' the UI
	onSelectCategory('Generic');
	onSelectElem('textField');
	
	$('#header_fields').click(function(){
		var options_html="";
		if($('#id_assoc_prog').attr('value')!="-1"){
			formElements['Program']=program_fields['fields'];
		}
		//Generating options for the category selector
		$.each(formElements,function(idx,el){
				options_html+="<option value="+idx+">"+idx+"</option>";
		});
		$('#cat_selector').html(options_html);
		onSelectCategory('Generic');
		onSelectElem('textField');
	});
	
	
	
	//csrf stuff
	$(document).ajaxSend(function(event, xhr, settings) {
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
	
	$('#form_toolbox').accordion({autoHeight:false, icons:{}});
	$.data($('div.outline')[0], 'data', {'question_text':'', 'help_text':''});

});


var createLabel=function(labeltext, required) {
	//Returns an HTML-formatted label, with a red * if the question is required
	
	if(!required)
		return '<p>'+labeltext+'</p>';
	else return '<p>'+labeltext+'<span class="asterisk">'+'*'+'</span></p>';	
};

var removeField = function() {
	//removes the selected element from the form by performing .remove() on the wrapper div
	
	if($(this).parent().hasClass('form_preview')){
		//If it's a page, remove the page-break text as well
		$(this).parent().prev().remove();
	}
	$(this).parent().remove();
};

var addOption=function(option_text) {
	//adds an option in the form toolbox
	
	var $option,$wrap_option;
	$wrap_option=$('<div></div>').addClass('option_element');
	$option=$('<input/>', {
		type:"text",
		value:option_text,
	});
	$option.appendTo($wrap_option);
	$('<input/>',{type:'button',value:'+'}).click(function(){addOption('')}).appendTo($wrap_option);
	$('<input/>',{type:'button',value:'-'}).click(removeOption).appendTo($wrap_option);
	$wrap_option.appendTo($('#multi_options'));
};

var removeOption=function() {
	//removes an option from the radio group
	
	$(this).parent().remove();
};

var generateOptions=function() {
	//Generates the options input fields for multi-select form fields
	
	for(i=1;i<=3;i++) {
		addOption('');
	}
};	

var getFirst=function(category){
	//returns the first item corresponding to category
	
	if(category=='Generic')
		return 'textField';
	else if(category=='Personal')
		return 'name';
	else if(category=='Program')
		return 'courses';
	else return '';	
};

var onSelectCategory=function(category) {
	//Populates the Field selector with the appropriate form fields
	
	var fields_list=formElements[category], options_html="";
	if(fields_list.length ==0)
		return;
	currCategory=category;
	//Generating Options list
	$.each(fields_list, function(index,elem){
		options_html+="<option value="+index+">"+elem['disp_name']+"</option>";
	});
	//Populating options for the Field Selector
	$("#elem_selector").html(options_html);
	
	//'Initializing' form builder with first field element
	onSelectElem(getFirst(category));
};

var clearSpecificOptions=function() {
	//Removes previous field-specific options, if any
	
	var $multi_options=$('#multi_options'),$other_options=$('#other_options');
	if($multi_options.children().length!=0)
		$multi_options.empty();
	if($other_options.children().length!=0)
		$other_options.empty();
}

var onSelectElem = function(item) {
	//Generates the properties fields when a form item is selected from the list
	
	//Remove previous field-specific options, if any
	clearSpecificOptions();
	$('#id_instructions').attr('value','');
	$('#id_required').attr('checked','');
	
	$('div.field_selected').removeClass('field_selected');
		
	var $option,$wrap_option,i, question_text=formElements[currCategory][item]['ques'], $button=$('#button_add');;
	
	//Defining actions for generic elements
	if(item=="radio" || item=="dropdown" || item=="multiselect" || item=="checkboxes") 
		generateOptions();
	else if(item=="numeric") {
		var $range_div=$('<div></div>').addClass('toolboxText');
		$minInput=$('<input/>', {
			type:"text",
			value:"0",
			name:"minVal",
			id:"id_minVal"
		});
		$maxInput=$('<input/>', {
			type:"text",
			value:"0",
			name:"maxVal",
			id:"id_maxVal"
		});
		
		$range_div.append($('<span>Min</span>')).append($minInput).append('&nbsp;&nbsp;').append($('<span>Max</span>')).append($maxInput);
		$range_div.appendTo($('#other_options'));
	}
	else if(item=='section'){
		$('#id_instructions').attr('value','Enter a short description about the section');
	}
	else if(item=='page'){
		$('#id_instructions').attr('value','Not required');
	}
	
	//Defining actions for 'personal' fields
	
	//Defining actions for custom fields	
	
	$('#id_question').attr('value',question_text);
	$prevField=$currSection.children(":last");
	if($button.attr('value')!='Add to Form')
		$button.attr('value','Add to Form').unbind('click').click(function(){insertField($('#elem_selector').attr('value'),$prevField)});
};

var updateField=function() {
	var curr_field_type=$.data($currField[0],'data').field_type;
	if(curr_field_type=='section'){
		$currField.find('h2').html($('#id_question').attr('value'));
		$currField.children('p.field_text').html($('#id_instructions').attr('value'));
		return;
	}
	$prevField=$currField.prev();
	$currField.remove();
	$currField=addElement(curr_field_type,$prevField);
	$currField.addClass('field_selected');
};

var onSelectField=function($elem, field_data) {
	/*
		Handles clicks on field wrappers.
		Also called by rebuild(..) to recreate a form from metadata
	*/
	
	clearSpecificOptions();
	//De-selecting any previously selected field
	$('div.field_selected').removeClass('field_selected');
	
	var $wrap=$elem, $button=$('#button_add'), options;
	
	if($wrap.length !=0){
		$wrap.removeClass('field_hover').addClass('field_selected');
		$wrap.find('.wrapper_button').removeClass('wrapper_button_hover');
		$currField=$wrap;
	}
	if(field_data.field_type!='section')
		$("#id_required").attr('checked',field_data.required);
	$("#id_question").attr('value',field_data.question_text);
	$("#id_instructions").attr('value',field_data.help_text);
	
	//Adding in field-specific options
	if($.inArray(field_data.field_type, ['radio', 'dropdown', 'multiselect', 'checkboxes']) != -1){
		options=field_data.attrs['options'].split("|");
		$.each(options, function(idx,el) {
			if(el!="")
				addOption(el);
		});
	}
	else if(field_data.field_type=='numeric'){
		var $range_div=$('<div></div>').addClass('toolboxText');
		var limits=field_data.attrs['limits'].split(',');
		$minInput=$('<input/>', {
			type:"text",
			value:limits[0],
			name:"minVal",
			id:"id_minVal"
		});
		$maxInput=$('<input/>', {
			type:"text",
			value:limits[1],
			name:"maxVal",
			id:"id_maxVal"
		});
		
		$range_div.append($('<span>Min</span>')).append($minInput).append('&nbsp;&nbsp;').append($('<span>Max</span>')).append($maxInput);
		$range_div.appendTo($('#other_options'));
	}
	else if(field_data.field_type=='section'){
		$("#id_required").attr('checked','');
	}
	if($button.attr('value')=='Add to Form')
		$button.attr('value','Update').unbind('click').click(updateField);
		
};

var deSelectField=function() {
	//De-selects 'this' field
	
	$(this).removeClass('field_selected');
	$(this).addClass('field_hover');
	$(this).find(".wrapper_button").toggleClass("wrapper_button_hover");
	$('#cat_selector').children('select[value=Generic]').attr('selected','selected');
	onSelectCategory('Generic');
	onSelectElem('textField');
}

var insertField=function(item, $prevField){
	//Handles addition of a field into the form, as well as other ancillary functions. Calls addElement()
	
	addElement(item,$prevField);
	onSelectElem(item);
}

var addElement = function(item,$prevField) {
	
	// This function adds the selected field to the form. Data like help-text is stored in the wrapper div using jQuery's $.data
	
	var i,$new_elem,$new_elem_label, 
		$wrap=$('<div></div>').addClass('field_wrapper').hover(function() {
			if($(this).hasClass('field_selected'))
				return;
			$(this).toggleClass('field_hover');
			$(this).find(".wrapper_button").toggleClass("wrapper_button_hover");
		}).toggle(function(){onSelectField($(this), $.data(this, 'data'));}, deSelectField),
		label_text=$.trim($('#id_question').attr('value')),
		help_text=$.trim($('#id_instructions').attr('value')),
		html_name=item+"_"+elemTypes[item], html_id="id_"+item+"_"+elemTypes[item],
		data={};
	
	$new_elem_label=$(createLabel(label_text,$('#id_required').attr('checked'))).appendTo($wrap);
	$('<input/>',{type:'button',value:'X'}).click(removeField).addClass("wrapper_button").appendTo($wrap);
	
	//Populating common data attributes
	data.question_text=label_text;
	data.help_text=help_text;
	data.field_type=item;
	data.required=$('#id_required').attr('checked');
	data.attrs={};
	
	//Generic fields first
	if(item=="textField"){
		$new_elem=$('<input/>', {
			type:"text",
			name:html_name,
			id:html_id,
			size:"30"
		});
	}
	else if(item=="longTextField"){
		$new_elem=$('<input/>', {
			type:"text",
			name:html_name,
			id:html_id,
			size:"60"
		});
	}
	else if(item=="longAns") {
		$new_elem=$('<textarea>', {
			name:html_name,
			id:html_id,
			rows:"8",
			cols:"50"
		});
	}
	else if(item=="reallyLongAns") {
		$new_elem=$('<textarea>', {
			name:html_name,
			id:html_id,
			rows:"14",
			cols:"70"
		});
	}
	else if(item=="radio") {
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$new_elem=$("<div>", {
			id:html_id
		});
		$text_inputs.each(function(idx,el) {
				$one_option=$('<input>', {
						type:"radio",
						name:html_name,
						value:$(el).attr('value')
				});
				options_string+=$(el).attr('value')+"|";	
				$new_elem.append($("<p>").append($one_option).append($("<span>"+$(el).attr('value')+"</span>")));
		});
		data['attrs']['options']=options_string;
	}
	else if(item=="dropdown") {
		$new_elem=$('<select>',{
			name:html_name,
			id:html_id
		});
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$text_inputs.each(function(idx,el) {
				$one_option=$('<option>', {
						value:$(el).attr('value')
				});	
				options_string+=$(el).attr('value')+"|";
				$one_option.html($(el).attr('value'));
				$new_elem.append($one_option);
		});
		data['attrs']['options']=options_string;
	}
	else if(item=="multiselect") {
		$new_elem=$('<select>',{
			name:html_name,
			id:html_id,
			'multiple':'multiple'
		});
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$text_inputs.each(function(idx,el) {
				$one_option=$('<option>', {
						value:$(el).attr('value')
				});	
				options_string+=$(el).attr('value')+"|";
				$one_option.html($(el).attr('value'));
				$new_elem.append($one_option);
		});
		data['attrs']['options']=options_string;
	}
	else if(item=="checkboxes"){
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$new_elem=$("<div>", {
			id:html_id
		});
		$text_inputs.each(function(idx,el) {
				$one_option=$('<input>', {
						type:"checkbox",
						name:html_name,
						value:$(el).attr('value')
				});
				options_string+=$(el).attr('value')+"|";	
				$new_elem.append($("<p>").append($one_option).append($("<span>"+$(el).attr('value')+"</span>")));
		});
		data['attrs']['options']=options_string;
	}
	else if(item=="numeric"){
		$new_elem=$('<input/>', {
			type:"text",
			name:html_name,
			id:html_id,
			size:"20"
		});
		data['attrs']['limits']=$('#id_minVal').attr('value') + ',' + $('#id_maxVal').attr('value');
	}
	else if(item=='date'){
		$new_elem=$("<div>", {
			id:html_id
		});
		var $mm,$dd,$yyyy;
		$mm=$('<input/>', {
			type:"text",
			name:html_name+"_mm",
			size:"2",
			value:"mm"
		});
		$dd=$('<input/>', {
			type:"text",
			name:html_name+"_dd",
			size:"2",
			value:"dd"
		});
		$yyyy=$('<input/>', {
			type:"text",
			name:html_name+"_yy",
			size:"4",
			value:"yyyy",
		});
		$new_elem.append($('<p>').append($mm).append($('<span> / </span>')).append($dd).append($('<span> / </span>')).append($yyyy));
	}
	else if(item=='time'){
		$new_elem=$("<div>", {
			id:html_id
		});
		var $hh,$m,$ss,$ampm;
		$hh=$('<input/>', {
			type:"text",
			name:html_name+"_hh",
			size:"2",
			value:"hh"
		});
		$m=$('<input/>', {
			type:"text",
			name:html_name+"_m",
			size:"2",
			value:"mm"
		});
		$ss=$('<input/>', {
			type:"text",
			name:html_name+"_ss",
			size:"2",
			value:"ss"
		});
		$ampm=$('<select>', {
			name:html_name+"_ampm"
		}).append($('<option value="AM">AM</option>')).append($('<option value="PM">PM</option>'));
		$new_elem.append($('<p>').append($hh).append($('<span> : </span>')).append($m).append($('<span> : </span>')).append($ss).append('&nbsp;').append($ampm));
	}
	else if(item=="file"){
		$new_elem=$('<input/>', {
			type:"file",
			name:html_name,
			id:html_id,
			size:"40"
		});
	}
	else if(item=='section'){
		//this one's processed differently from the others
		
		var $outline=$('<div class="outline"></div>');
		$outline.append('<hr/>').append($('<h2 class="section_header">'+label_text+'</h2>')).append($('<p class="field_text">'+help_text+'</p>'));
		$currSection=$('<div>', {
			id:'section_'+secCount,
			'class':'section'
		});
		$outline.append($currSection);
		$('<input/>',{type:'button',value:'X'}).click(removeField).addClass("wrapper_button").appendTo($outline);
		$outline.toggle(function() {
			onSelectField($(this), $.data(this, 'data'));
			$(this).children(".wrapper_button").addClass("wrapper_button_hover");
		}, function(){
			$(this).children(".wrapper_button").removeClass("wrapper_button_hover");
			$(this).removeClass('field_selected');
			$('#cat_selector').children('select[value=Generic]').attr('selected','selected');
			onSelectCategory('Generic');
			onSelectElem('textField');
		});
		$outline.appendTo($currPage).dblclick(function(){
			$currSection=$(this).children('div.section');
		});
		$currPage.sortable();
		secCount++;
		$.data($outline[0],'data',data);
		return $outline;
	}
	else if(item=='page'){
		//First putting in the page break text
		var $page_break = $('<div class="page_break"><span>** Page Break **</span></div>');
		$page_break.appendTo($('div.preview_area'));
		
		//Now putting in the page div
		$currPage=$('<div class="form_preview"></div>');
		$currSection=$('<div class="section"></div>');
		$currPage.append($('<div class="outline"></div>').append($currSection));
		$('<input/>',{type:'button',value:'X'}).click(removeField).addClass("wrapper_button").appendTo($currPage);
		$currPage.toggle( function(){$(this).children(".wrapper_button").addClass("wrapper_button_hover");}, 
						function(){$(this).children(".wrapper_button").removeClass("wrapper_button_hover");});
		$currPage.dblclick(function(){
			$currPage=$(this);
		});
		$currPage.appendTo($('div.preview_area'));
		$.data(($currSection.parent())[0], 'data', {'question_text':'', 'help_text':''});
		return $currPage;
	}
	
	//'Personal Information' Fields
	else if(item=="name"){
		$new_elem=$('<div>').css('display','inline-block');
		var $first_div, $last_div;
		$first_div=$('<div>').append($('<input/>',{
			type:'text',
			size:'20'
		})).append($('<p class="field_text">First</p>')).css('float','left');
		$last_div=$('<div>').append($('<input/>',{
			type:'text',
			size:'20'
		})).append($('<p class="field_text">Last</p>')).css('float','left');
		$new_elem.append($first_div).append($last_div).append('<br/>');
	}
	else if(item=='gender'){
		$new_elem=$('<p>');
		$new_elem.append($('<input/>', {
			type:'radio',
			value:'Male',
			name:'gender'
		})).append($('<span class="field_text">Male&nbsp;&nbsp;</span>')).append($('<input/>', {
				type:'radio',
				value:'Female',
				name:'gender'
		})).append($('<span class="field_text">Female</span>'))
	}	
	else if(item=="phone"){
		$new_elem=$('<input/>', {
			type:"text",
			size:'30'
		});
	}
	else if(item=='email'){
		$new_elem=$('<input/>', {
			type:"email",
			size:'30'
		});
	}
	else if(item=='address'){
		$new_elem=$('<div>');
		$new_elem.append($('<p class="field_text">Street Address</p>')).append($('<textarea>',{
			'rows':4,
			'cols':22
		}));
		$new_elem.append($('<p>').append($('<span class="field_text">City&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>')).append($('<input/>', {
			type:'text',
			size:'20'
		})).append('&nbsp;&nbsp;').append($('<span class="field_text">State</span>')).append($('<select>')));
		$new_elem.append($('<p>').append($('<span class="field_text">Zip code</span>')).append($('<input/>',{
			type:'text'
		})));
	}
	else if(item=='state'){
		$new_elem=$('<select>');
	}
	else if(item=='city'){
		$new_elem=$('<input/>', {
			type:"text",
			size:'30'
		});
	}
	else if(item=='courses'){
		$new_elem=$('<select>');
	}
	
	elemTypes[item]++;
	$new_elem.appendTo($wrap);
	$.data($wrap[0],'data',data);
	
	if($prevField.length==0)
		$wrap.prependTo($currSection);
	else
		$wrap.insertAfter($prevField);
	
	//Making fields draggable
	$currSection.sortable();
	return $wrap;
};

var submit=function() {
	//submits the created form to the server
	
	var form={'title':$('#form_title').html(), 'desc':$('#form_description').html(), 'anonymous':String($('#id_anonymous').attr('checked')), 'pages':[]}, section, elem, page, section_seq;
	if($('#id_assoc_prog').val()!="-1") {
		form['link_type']='program';
		form['link_id']=$('#id_assoc_prog').val();
	}
	else {
		form['link_type']='none';
		form['link_id']='-1';
	}
	
	//Constructing the object to be sent to the server
	$('div.preview_area').children('div.form_preview').each(function(pidx,pel) {
		page={'sections':[]};
		section_seq=0;
		$(pel).children('div.outline').each(function(idx, el) {
			section={'data':$.data(el, 'data'), 'fields':[]};
			section['data']['seq']=section_seq;
			delete(section['data']['required']);

			//Putting fields inside a section
			$(el).children('div.section').children().each(function(fidx, fel) {
				if( $(fel).hasClass('field_wrapper')){
					elem={'data':$.data(fel,'data')};
					elem['data']['seq']=fidx;
					elem['data']['required']=String(elem['data']['required']);
					section['fields'].push(elem);
				}
			});
			if(section['fields'].length!=0){
				//Put section inside page if section is non-empty
				page['sections'].push(section);
				section_seq++;
			}	
		});
		//Putting the page inside the form
		if(page['sections'].length!=0)
			form['pages'].push(page);
	});
	if(form['pages'].length==0){
		alert("Sorry, that's an empty form.");
		return;
	}
	console.log(form);
	//POSTing to server
	$.ajax({
		url:'/customforms/submit/',
		data:JSON.stringify(form),
		type:'POST',
		success: function(value) {
			console.log(value);
			if(value=='OK')
				window.location='/customforms/';
		}
	});
	$('#submit').attr("disabled","true");
		
};

var updateTitle = function(){
	//Updates the title for the form
	
	$("#form_title").html($('#input_form_title').attr('value'));
};

var updateDesc=function() {
	//Updates the form description
	$('#form_description').html($('#input_form_description').attr('value'));
	
};

var createFromBase=function(){
	//Clearing previous fields, if any
	$('div.form_preview').remove();
	$('div.page_break').remove();
	$currPage=$('<div class="form_preview"></div>');
	$currSection=$('<div class="section"></div>');
	$currPage.append($('<div class="outline"></div>').append($currSection));
	$('div.preview_area').append($currPage);
	
	var base_form_id=$('#base_form').val();
	if(base_form_id!="-1"){
		$.ajax({
			url:'/customforms/metadata/',
			data:{'form_id':base_form_id},
			type:'GET',
			dataType:'json',
			async:false,
			success: function(metadata) {
				console.log(metadata);
				rebuild(metadata);
			}
		});
	}
};

var rebuild=function(metadata) {
	//Takes form metadata, and reconstructs the form from it
	
	$('#outline_0').remove();
	//Setting form's title and description
	$('#input_form_title').attr('value', metadata['title']).change();
	$('#input_form_description').attr('value',metadata['desc']).change();
	
	//Setting other form options
	if(metadata['anonymous'])
		$('#id_anonymous').attr('checked', true);
	if(metadata['link_type']=='program')
		$('#id_assoc_prog').val(metadata['link_id'])
		
	//Putting in pages, sections and fields
	$.each(metadata['pages'], function(pidx, page){
		if(pidx!=0)
			addElement('page',[]);
			
		$.each(page, function(sidx, section){
			$('#id_question').val(section[0]['section__title']);
			$('#id_instructions').val(section[0]['section__description']);
			var $outline=addElement('section',[]);
			if(sidx==0){
				//Removing the <hr> that comes before every section
				$outline.find('hr').remove();
			}
			$prevField=[];
			$.each(section, function(fidx, field){
				/*
					The idea is to collect a field's metadata in the format expected, and
					then call onSelectField(...) passing it the metadata. onSelectField()
					will populate stuff like label, options etc. in the toolbox, and then we
					can call insertField(...). This is slightly roundabout, but hey, DRY.
				*/
				var field_data={
					question_text:field['label'],
					help_text:field['help_text'],
					field_type:field['field_type'],
					required: field['required'],
					attrs:{}
				};
				
				
				if($.inArray(field['attribute__attr_type'], ['options', 'limits'])!=-1)
					field_data.attrs[field['attribute__attr_type']]=field['attribute__value'];	
				onSelectField([], field_data);	
				$prevField=addElement(field['field_type'], $prevField);	
			});
		});
	});	
	
};

