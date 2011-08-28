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
		section:{'disp_name':'Section', 'ques':'Section'},
		page:{'disp_name':'Page', 'ques':'Page'}
	},
    'Personal':
    {
    	phone:{'disp_name':'Phone no.','ques':'Your phone no.'},
		email:{'disp_name':'Email','ques':'Your email'},
		state:{'disp_name':'State','ques':'Your state'},
        gender:{'disp_name':'Gender','ques':'Your gender'}
    },  
    'NotReallyFields': {
        instructions: {'disp_name': 'Instructions', 'ques': ''}
    },
	/*'Personal':{
		name:{'disp_name':'Name','ques':'Your name', 'field_type':'custom', 'field_options':{}},
		gender:{'disp_name':'Gender','ques':'Gender', 'field_type':'radio', 'field_options':{'options':'Male|Female'}},
		phone:{'disp_name':'Phone no.','ques':'Phone no.', 'field_type':'textField', 'field_options':{}},
		email:{'disp_name':'Email','ques':'Email', 'field_type':'textField', 'field_options':{}},
		address:{'disp_name':'Address','ques':'Address', 'field_type':'custom', 'field_options':{}},
		state:{'disp_name':'State','ques':'State', 'field_type':'dropdown', 'field_options':{'options':''}},
		city:{'disp_name':'City','ques':'City', 'field_type':'textField', 'field_options':{}}
	},
	'Program':{}*/
};

var getKeys = function(obj){
   var keys = [];
   for(var key in obj){
      keys.push(key);
   }
   return keys;
}
var default_categories = getKeys(formElements);

var inDefaultCategory = function(field_type) {
    for (var catname in formElements)
    {
        for (var catlabel in formElements[catname])
        {
            if (field_type == catlabel)
                return true;
        }
    }
    return false;
}

var only_fkey_models=[];

var model_instance_cache={};

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
	'courses':0,
    'radio_yesno': 0,
    'boolean': 0,
    'null_boolean': 0,
    'instructions': 0
};

var currElemType, currElemIndex, optionCount=1, formTitle="Form",$prevField, $currField, secCount=1, $currSection, pageCount=1, $currPage;
var perms={};

$(document).ready(function() {
	
	//Assigning event handlers
    $('#button_add').click(function(){insertField($('#elem_selector').attr('value'),$prevField)});
	$('#submit').click(submit);
	$('#input_form_title').bind('change', updateTitle);
	$('#input_form_description').bind('change', updateDesc);
	$('#id_main_perm').change(onChangeMainPerm);
	$('#id_prog_belong').change(onChangeProgBelong);
	$('#links_id_main').change(onChangeMainLink);
	$('#links_id_specify').change(onChangeLinksSpecify);
	$('#id_modify').change(function(){
		if($(this).attr('checked'))
			$('#submit').val('Modify Form');
		else $('#submit').val('Create Form');	
	});
	$('#cat_selector').change(function(){onSelectCategory($(this).val());});
	$('#elem_selector').change(function(){onSelectElem($('#elem_selector').val());});
	$('#main_cat_spec').change(onChangeMainCatSpec);
	$('#id_perm_program').change(onChangePermProg);
	
	$currSection=$('#section_0');
	$currPage=$('#page_0');
	$('<input/>',{type:'button',value:'X'}).click(removeField).addClass("wrapper_button").appendTo($currPage);	
	
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
	$.data($currPage[0], 'data', {'parent_id':-1});
	
	$("#page_break_0").dblclick(function(){
		$currPage=$(this).next('div.form_preview'); 
		//$currSection=$(this).children(":last").children("div.section");
	}).toggle(function(){$(this).next('div.form_preview').children(".wrapper_button").addClass("wrapper_button_hover");}, 
			function(){$(this).next('div.form_preview').children(".wrapper_button").removeClass("wrapper_button_hover");}
			);
	
	//Getting field information from server, and constructing the form-builder
	constructBuilder();		
	
	//Initializing UI
	//initUI();
});

var getFieldCategory=function(field_type) {
	//Returns the category for this field
	var cat="";
	$.each(formElements, function(category, fields){
		if(field_type in fields){
			cat=category;
			return false; //break out
		}
	});
	return cat;
}

var constructBuilder = function(){
	//Constructs the form builder with field information from the server
	
	$.ajax({
		url:'/customforms/builddata/',
		type:'GET',
		dataType:'json',
		async:false,
		success: function(field_data) {
			only_fkey_models.push.apply(only_fkey_models, field_data['only_fkey_models']);
			//Putting in link fields
			$.each(field_data['link_fields'], function(category, fields){
				formElements[category]={};
				model_instance_cache[category]={'options':{}, 'selected_inst':"-1", 'selected_cat':'-1'};
				$.extend(formElements[category], fields);
			});
			initUI();
		}
	});
};

var clearCatOptions=function() {
	$('#cat_instance_sel').html('').hide();
	$('#cat_spec_options').hide();
};

var initUI=function(){
	//Sets up the initial options
	var options_html="";
	//Generating options for the category selector
	$.each(formElements,function(idx,el){
			if(!$.isEmptyObject(el))
				options_html+="<option value="+idx+">"+idx+"</option>";
	});
	$('#cat_selector').html(options_html);
	
	//Putting in options for the "Links" tab
	options_html='<option value="-1">None</option>';
	$.each(only_fkey_models, function(idx, el){
		options_html+="<option value="+el+">"+el+"</option>";
	});
	$('#links_id_main').html(options_html);
	
	onSelectCategory('Generic');
	onSelectElem('textField');
	perms={};
	clearPermsArea();
	$('#id_modify_wrapper').hide();
	clearLinksArea();
	clearCatOptions();
};

var clearPermsArea=function(){
	//Initializes the permissions area
	$('#id_prog_belong').attr('checked', false).parent().hide();
	$('#id_perm_program').val("-1").hide();
	$('#id_sub_perm').children().remove();
	$('#id_sub_perm').parent().hide();
};

var clearLinksArea=function(){
	//Clears up the links area
	$('#links_id_specify').val('userdef').parent().hide();
	$('#links_id_pick').empty().parent().hide();
};

var onChangeMainLink=function(){
	clearLinksArea();
	if($('#links_id_main').val()!='-1')
		$('#links_id_specify').parent().show();
	else $('#links_id_specify').parent().hide();	
};

var onChangeLinksSpecify=function(){
	if($('#links_id_specify').val()=='particular'){
		$.ajax({
			url:'/customforms/getlinks/',
			data:{'link_model':$('#links_id_main').val()},
			type:'GET',
			dataType:'json',
			async:false,
			success: function(link_objects) {
				var html_str='';
				$.each(link_objects, function(id, name){
					html_str+='<option value="'+id+'">'+name+'</option>';
				});
				$('#links_id_pick').html(html_str);
				$('#links_id_pick').parent().show();
			}
		});
	}
	else{
		$('#links_id_pick').html('');
		$('#links_id_pick').parent().hide();
	}
};

var getPerms=function(prog_id){
	//Queries the server for perms related to the currently selected program
	if(prog_id!="-1"){
		$.ajax({
			url:'/customforms/getperms/',
			data:{'prog_id':prog_id},
			type:'GET',
			dataType:'json',
			async:false,
			success: function(retval) {
				console.log(retval);
				perms=retval;
				populatePerms(perms);
			}
		});
	}
	else perms={};
};

var setPerms=function(){
	//Sets the permission options based on selected values
	
	var prog_id=$('#id_perm_program').val();
	if(prog_id=="-1")
		return;
	if($.isEmptyObject(perms))
		getPerms(prog_id);
	else populatePerms(perms);	
};

var populatePerms=function(perm_opts){
	var options=[], main_perm, options_string='';
	main_perm=$('#id_main_perm').val();
	if(main_perm!="none"){
		if(main_perm=='Teacher') options=perm_opts['teachers'];
		else if(main_perm=='Student') options=perm_opts['students'];
		
		$.each(options, function(idx, el){
			options_string+='<option value='+el[0]+'>'+el[1]+'</option>';
		});
		$('#id_sub_perm').html(options_string).parent().show();
	}
};

var onChangeMainPerm=function(){
	clearPermsArea();
	var main_perm=$(this).val();
	if(main_perm!='none'){
		$('#id_prog_belong').parent().show();
	}
};

var onChangeProgBelong=function(){
	var belongs=$(this).attr('checked');
	if(belongs){
		$('#id_perm_program').show();
	}
	else {
		$('#id_sub_perm').parent().hide();
		$('#id_perm_program').val("-1").hide();
	}
};

var onChangePermProg=function(){
	var prog=$('#id_perm_program');
	if(prog!="-1"){
		setPerms();
		$('#id_sub_perm').parent().show();
	}
	else
		$('#id_sub_perm').parent().hide();
};

var onChangeMainCatSpec=function() {
	//Fetches instances from the server, populates values etc.
	//Used to set up options for non-generic categories
	$("#cat_instance_sel").html('');
	
	var main_cat_spec=$("#main_cat_spec").val(), curr_category=$("#cat_selector").val(), options_html="";
	if(main_cat_spec != "automatic") {
		if($.isEmptyObject(model_instance_cache[curr_category]['options'])){
			//Fetch values from the server, and store in the cache
			$.ajax({
				url:'/customforms/getlinks/',
				data:{'link_model':curr_category},
				type:'GET',
				dataType:'json',
				async:false,
				success: function(link_objects) {
					$.each(link_objects, function(id, name){
						model_instance_cache[curr_category]['options'][id]=name;
					});
				}
			});
		}	
		
		//Set options from the cache
		$.each(model_instance_cache[curr_category]['options'], function(idx, el){
			options_html+="<option value="+idx+">"+el+"</option>";
		});
		$("#cat_instance_sel").html(options_html);
		//If this option has been set previously, fetch it from the cache and set it
		if(model_instance_cache[curr_category]['selected_inst'] != "-1")
			$("#cat_instance_sel").val(model_instance_cache[curr_category]['selected_inst']);
			
		//Show the instance selector
		$("#cat_instance_sel").show();	
	}
	else
		$("#cat_instance_sel").hide();
};	

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
	//returns some item corresponding to category
	
	var retval="";
	$.each(formElements[category], function(idx, el){retval=idx; return false;});
	return retval;
};


var showCategorySpecificOptions=function(category){
	//Shows options related to the current category.
	//For instance, for linked fields, it shows options for selecting the queryset.
	clearCatOptions();
	
    //  Don't show anything unless the selected category came from a linked model
    for (var c in default_categories)
    {
        if (default_categories[c] == category)
            return;
    }

    //Show the category-specific options
    $('#cat_spec_options').show();
    
    //Set any-predefined values
    if(category in model_instance_cache){
        if(model_instance_cache[category]['selected_cat']!="-1"){
            $('#main_cat_spec').val(model_instance_cache[category]['selected_cat']);
            onChangeMainCatSpec();
        }
    }
};

var populateFieldsSelector=function(category){
	//Populates the Field selector with the appropriate form fields
	
	var fields_list=formElements[category], options_html="";
	if(fields_list.length ==0)
		return;
	//Generating Options list
	$.each(fields_list, function(index,elem){
		var disp_name="";
		if(category!="Generic" && elem['required'])
			disp_name=elem['disp_name']+"**";
		else disp_name=elem['disp_name'];	
		options_html+="<option value="+index+">"+disp_name+"</option>";
	});
	//Populating options for the Field Selector
	$("#elem_selector").html(options_html);
};

var onSelectCategory=function(category) {
	//Handles selection of a particular category
	
	populateFieldsSelector(category);
	
	//'Initializing' form builder with first field element
	onSelectElem(getFirst(category));
	showCategorySpecificOptions(category);
};

var clearSpecificOptions=function() {
	//Removes previous field-specific options, if any
	
	var $multi_options=$('#multi_options'),$other_options=$('#other_options');
	if($multi_options.children().length!=0)
		$multi_options.empty();
	if($other_options.children().length!=0)
		$other_options.empty();
};

var addSpecificOptions=function(elem, options, limtype) {
	//Adds in specific options for some fields

	var limits, frag, $div;
	if(elem=='numeric'){
		if(options!='')
			limits=options.split(',');
		else limits=[0,0];
		frag='<div class="toolboxText">';
		frag+='<p>Min <input type="text" id="id_minVal" value="'+limits[0]+'"/>';
		frag+='&nbsp;&nbsp;Max <input type="text" id="id_maxVal" value="'+limits[1]+'"/>';
		frag+='</p></div>';
	 	$div=$(frag);
		$div.appendTo($('#other_options'));	
	}
	else if(elem=='textField' || elem=='longTextField' || elem=='longAns' || elem=='reallyLongAns'){
		if(options!='')
			limits=options.split(',');
		else limits=['',''];
		frag='<div id="text_limits" class="toolboxText">';
		frag+='<select id="charOrWord">';
		frag+='<option value="chars">Characters</option>';
		frag+='<option value="words">Words</option>';
		frag+='</select>';
		frag+='<p>Min <input type="text" id="text_min" value="'+limits[0]+'"/> &nbsp;&nbsp;'; 
		frag+='Max <input type="text" id="text_max" value="'+limits[1]+'"/></p>';
		frag+='</div>';
		var $div=$(frag);
		$div.appendTo($('#other_options'));
		if(limtype!='')
			$('#charOrWord').val(limtype);
		else $('#charOrWord').val('chars');
	}
};

var addCorrectnessOptions = function(elem) {
    /*  Display a field that lets the form author specify a "correct" answer
        for supported field types   */

    //  TODO: Convert the correct answer selector into a replica of the field
    //  that the user will see.  For now, they have to know kung fu.
    if (elem == 'dropdown')
    {
        frag = '<div id="dropdown_correctness_options" class="toolboxText">';
        frag += '<p>Correct answer index: ';
        frag += '<input type="text" id="dropdown_correct_answer" value=""/>';
        frag += '</p></div>';
        var $div = $(frag);
        $div.appendTo($('#other_options'));
    }
    else if (elem == 'radio')
    {
        frag = '<div id="radio_correctness_options" class="toolboxText">';
        frag += '<p>Correct answer index: ';
        frag += '<input type="text" id="radio_correct_answer" value=""/>';
        frag += '</p></div>';
        var $div = $(frag);
        $div.appendTo($('#other_options'));
    }
    else if (elem == 'textField')
    {
        frag = '<div id="textField_correctness_options" class="toolboxText">';
        frag += '<p>Correct answer: ';
        frag += '<input type="text" id="textField_correct_answer" value=""/>';
        frag += '</p></div>';
        var $div = $(frag);
        $div.appendTo($('#other_options'));
    }
    else if (elem == 'checkboxes')
    {
        frag = '<div id="checkboxes_correctness_options" class="toolboxText">';
        frag += '<p>Correct answer indices (comma-separated): ';
        frag += '<input type="text" id="checkboxes_correct_answer" value=""/>';
        frag += '</p></div>';
        var $div = $(frag);
        $div.appendTo($('#other_options'));
    }
}

var onSelectElem = function(item) {
	//Generates the properties fields when a form item is selected from the list

	//Remove previous field-specific options, if any
	clearSpecificOptions();
	$('#id_instructions').attr('value','');
	$('#id_required').attr('checked','');
	
	$('div.field_selected').removeClass('field_selected');
	var currCategory=$('#cat_selector').val();	
	var $option,$wrap_option,i, question_text=formElements[currCategory][item]['ques'], $button=$('#button_add');
	
    //  Add validation options
    if (item in formElements['Generic'])
    {
        addCorrectnessOptions(item);
    }
    
	//Defining actions for generic elements
	if(item=='textField' || item=='longTextField' || item=='longAns' || item=='reallyLongAns')
		addSpecificOptions(item, '', '');
	else if(item=="radio" || item=="dropdown" || item=="multiselect" || item=="checkboxes") 
		generateOptions();
	else if(item=="numeric") 
		addSpecificOptions(item, '', '');
	else if(item=='section'){
		$('#id_instructions').attr('value','Enter a short description about the section');
	}
	else if(item=='page'){
		$('#id_instructions').attr('value','Not required');
	}
	
	//Set 'Required' to a sensible default
	setRequired(item);	
		
	$('#id_question').attr('value',question_text);
	$prevField=$currSection.children(":last");
	if($button.attr('value')!='Add to Form')
		$button.attr('value','Add to Form').unbind('click').click(function(){insertField($('#elem_selector').attr('value'),$prevField)});
};

var setRequired=function(item){
	//Sets the 'Required' option according to item
	
	$('#id_required').attr('disabled', false);
	//For 'section' and 'page', disable 'Required'
	if(item=='page' || item=='section' || item in formElements['NotReallyFields'])
		$('#id_required').attr('disabled', true);
	//Set 'Required' as checked for custom fields that are required on the model
	if(!item in formElements['Generic']){
		//Get the options for this item, and set 'Required' accordingly
		$.each(formElements, function(cat, flds){
			if(item in flds){
				if(flds[item]['required'])
					$('#id_required').attr('checked', true).attr('disabled', true);
				return false; //break out
			}
		});
	}	
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
		
	var $wrap=$elem, $button=$('#button_add'), options, ftype=field_data.field_type;
	
	//Select the current field and category in the field and category selectors
	if(ftype in formElements['Generic']){
		$('#cat_selector').val('Generic');
		populateFieldsSelector('Generic');
		$('#elem_selector').val(ftype);	
	}
	else if(ftype in formElements['Personal']){
		$('#cat_selector').val('Personal');
		populateFieldsSelector('Personal');
		$('#elem_selector').val(ftype);
	}
	else {
		//link field
		var curr_cat=getFieldCategory(ftype);
		$('#cat_selector').val(curr_cat);
		populateFieldsSelector(curr_cat);
		$('#elem_selector').val(ftype);
		showCategorySpecificOptions(curr_cat);
	}
	
	if($wrap.length !=0){
		$wrap.removeClass('field_hover').addClass('field_selected');
		$wrap.find('.wrapper_button').removeClass('wrapper_button_hover');
		$currField=$wrap;
		$currSection=$wrap.parent();
		$prevField=$wrap.prev('div.field_wrapper');	
	}
	if(ftype!='section')
		$("#id_required").attr('checked',field_data.required);
	$("#id_question").attr('value',field_data.question_text);
	$("#id_instructions").attr('value',field_data.help_text);
	
	//Adding in field-specific options
	if($.inArray(ftype, ['radio', 'dropdown', 'multiselect', 'checkboxes']) != -1){
		options=field_data.attrs['options'].split("|");
		$.each(options, function(idx,el) {
			if(el!="")
				addOption(el);
		});
	}
	else if(ftype=='numeric')
		addSpecificOptions('numeric', field_data.attrs['limits'], '');
	else if($.inArray(ftype, ['textField', 'longTextField', 'longAns', 'reallyLongAns']) != -1){
		var key;
		if('charlimits' in field_data.attrs)
			addSpecificOptions(ftype, field_data.attrs['charlimits'], 'chars');
		else
			addSpecificOptions(ftype, field_data.attrs['wordlimits'], 'words');
	}
	else if(ftype=='section'){
		$("#id_required").attr('checked','');
	}
	if($button.attr('value')=='Add to Form')
		$button.attr('value','Update').unbind('click').click(updateField);
		
	//Set 'Required' depending on item
	setRequired(ftype);	
};

var deSelectField=function() {
	//De-selects 'this' field
	
	$(this).removeClass('field_selected');
	$(this).addClass('field_hover');
	$(this).find(".wrapper_button").toggleClass("wrapper_button_hover");
	$('#cat_selector').children('option[value=Generic]').attr('selected','selected');
	onSelectCategory('Generic');
	onSelectElem('textField');
};

var insertField=function(item, $prevField){
	//Handles addition of a field into the form, as well as other ancillary functions. Calls addElement()
	
	addElement(item,$prevField);
	onSelectElem(item);
};

var renderNormalField=function(item, field_options, data){
	//Rendering code for simple fields (i.e. non-custom fields)
	var $new_elem, key;
	if(item=="textField"){
		$new_elem=$('<input/>', {
			type:"text",
			size:"30"
		});
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
        data['attrs']['correct_answer']=$('#textField_correct_answer').attr('value');
	}
	else if(item=="longTextField"){
		$new_elem=$('<input/>', {
			type:"text",
			size:"60"
		});
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
	}
	else if(item=="longAns") {
		$new_elem=$('<textarea>', {
			rows:"8",
			cols:"50"
		});
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
	}
	else if(item=="reallyLongAns") {
		$new_elem=$('<textarea>', {
			rows:"14",
			cols:"60"
		});
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
	}
	else if(item=="radio") {
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$new_elem=$("<div>");
		
		if(!$.isEmptyObject(field_options)){
			//Custom field, get options from definition
			options_string=field_options['options'];
		}
		else {
			//Normal field
			$text_inputs.each(function(idx,el) {
					options_string+=$(el).attr('value')+"|";	
			});
		}
		$.each(options_string.split('|'), function(idx, el){
			if(el!=''){
				$one_option=$('<input>', {
						type:"radio",
						value:el
				});
				$new_elem.append($("<p>").append($one_option).append($("<span>"+el+"</span>")));
			}
		});
		data['attrs']['options']=options_string;
        data['attrs']['correct_answer']=$('#radio_correct_answer').attr('value');
	}
	else if(item=="dropdown") {
		$new_elem=$('<select>');
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		if(!$.isEmptyObject(field_options))
			options_string=field_options['options'];
		else{
			$text_inputs.each(function(idx,el) {
				options_string+=$(el).attr('value')+"|";
			});
		}
		$.each(options_string.split('|'), function(idx, el){
			if(el!=''){
				$one_option=$('<option>', {
						value:el
				});	
				$one_option.html(el);
				$new_elem.append($one_option);
			}
		});	
        data['attrs']['correct_answer']=$('#dropdown_correct_answer').attr('value');
		data['attrs']['options']=options_string;
	}
	else if(item=="multiselect") {
		$new_elem=$('<select>',{
			'multiple':'multiple'
		});
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		if(!$.isEmptyObject(field_options))
			options_string=field_options['options'];
		else {
			$text_inputs.each(function(idx,el) {
				options_string+=$(el).attr('value')+"|";
			});
		}
		$.each(options_string.split('|'), function(idx, el){
			$one_option=$('<option>', {
					value:el
			});	
			$one_option.html(el);
			$new_elem.append($one_option);
		});	
		data['attrs']['options']=options_string;
	}
	else if(item=="checkboxes"){
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$new_elem=$("<div>");
		if(!$.isEmptyObject(field_options))
			options_string=field_options['options'];
		else {
			$text_inputs.each(function(idx,el) {
				options_string+=$(el).attr('value')+"|";
			});
		}
		$.each(options_string.split('|'), function(idx, el){
			$one_option=$('<input>', {
					type:"checkbox",
					value:el
			});
			$new_elem.append($("<p>").append($one_option).append($("<span>"+el+"</span>")));
		});
		data['attrs']['options']=options_string;
        data['attrs']['correct_answer']=$('#checkboxes_correct_answer').attr('value');
	}
	else if(item=="numeric"){
		$new_elem=$('<input/>', {
			type:"text",
			size:"20"
		});
		data['attrs']['limits']=$('#id_minVal').attr('value') + ',' + $('#id_maxVal').attr('value');
	}
	else if(item=='date'){
		$new_elem=$("<div>");
		var $mm,$dd,$yyyy;
		$mm=$('<input/>', {
			type:"text",
			size:"2",
			value:"mm"
		});
		$dd=$('<input/>', {
			type:"text",
			size:"2",
			value:"dd"
		});
		$yyyy=$('<input/>', {
			type:"text",
			size:"4",
			value:"yyyy",
		});
		$new_elem.append($('<p>').append($mm).append($('<span> / </span>')).append($dd).append($('<span> / </span>')).append($yyyy));
	}
	else if(item=='time'){
		$new_elem=$("<div>");
		var $hh,$m,$ss,$ampm;
		$hh=$('<input/>', {
			type:"text",
			size:"2",
			value:"hh"
		});
		$m=$('<input/>', {
			type:"text",
			size:"2",
			value:"mm"
		});
		$ss=$('<input/>', {
			type:"text",
			size:"2",
			value:"ss"
		});
		$ampm=$('<select>').append($('<option value="AM">AM</option>')).append($('<option value="PM">PM</option>'));
		$new_elem.append($('<p>').append($hh).append($('<span> : </span>')).append($m).append($('<span> : </span>')).append($ss).append('&nbsp;').append($ampm));
	}
	else if(item=='phone' || item=='email'){
		$new_elem=$('<input/>', {
			type:"text",
			size:"30"
		});
	}
	else if(item=='state'){
		$new_elem=$('<select></select>');
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
		})).append($('<span class="field_text">Female</span>'));
	}
    else if((item=="boolean") || (item == "null_boolean")) {
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$new_elem=$("<div>");
        options_string = 'Yes';
		$.each(options_string.split('|'), function(idx, el){
			$one_option=$('<input>', {
					type:"checkbox",
					value:el
			});
			$new_elem.append($("<p>").append($one_option).append($("<span>"+el+"</span>")));
		});
		data['attrs']['options']=options_string;
	}
    else if(item=="radio_yesno") {
		var $text_inputs=$('#multi_options input:text'), $one_option, options_string="";
		$new_elem=$("<div>");
		
		options_string = 'Yes|No';
		$.each(options_string.split('|'), function(idx, el){
			if(el!=''){
				$one_option=$('<input>', {
						type:"radio",
						value:el
				});
				$new_elem.append($("<p>").append($one_option).append($("<span>"+el+"</span>")));
			}
		});
		data['attrs']['options']=options_string;
	}
    else if(item=="instructions") {
		$new_elem=$('<div class="instructions">' + $('#id_instructions').attr('value') + '</div>');
	}
	//Page and section are special-cased
	else if(item=='section'){
		//this one's processed differently from the others
	
		var $outline=$('<div class="outline"></div>'), label_text=$.trim($('#id_question').attr('value')),
			help_text=$.trim($('#id_instructions').attr('value'));
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
		$page_break.dblclick(function(){
			$currPage=$(this).next('div.form_preview'); 
			//$currSection=$(this).children(":last").children("div.section");
		}).toggle(function(){$(this).next('div.form_preview').children(".wrapper_button").addClass("wrapper_button_hover");}, 
				function(){$(this).next('div.form_preview').children(".wrapper_button").removeClass("wrapper_button_hover");}
				).appendTo($('div.preview_area'));
		
		//Now putting in the page div
		$currPage=$('<div class="form_preview"></div>');
		$currSection=$('<div class="section"></div>');
		$currPage.append($('<div class="outline"></div>').append($currSection));
		$('<input/>',{type:'button',value:'X'}).click(removeField).addClass("wrapper_button").appendTo($currPage);
		$currPage.toggle( function(){$(this).children(".wrapper_button").addClass("wrapper_button_hover");}, 
						function(){$(this).children(".wrapper_button").removeClass("wrapper_button_hover");});
		$currPage.dblclick(function(){
			$currPage=$(this);
			//$currSection=$(this).children(":last").children("div.section");
		});
		$currPage.appendTo($('div.preview_area'));
		$.data(($currSection.parent())[0], 'data', {'question_text':'', 'help_text':'', 'parent_id':-1});
		$.data($currPage[0], 'data', {'parent_id':-1});
		return $currPage;
	}
	return $new_elem; 
};

var renderCustomField=function(item, field_options, data){
	//Rendering code for custom fields

	var $new_elem;
	if(item.match("name$")){
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
	else if(item.match("address$")){
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
	
	return $new_elem;
};

var addElement=function(item, $prevField) {
	// This function adds the selected field to the form. 
	//Data like help-text is stored in the wrapper div using jQuery's $.data

	var i,$new_elem_label, $new_elem, 
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
	data.parent_id=-1; //Useful for modifications
	data.attrs={};
	
	//Special-casing page and section
	if(item=='page' || item=='section')
		return renderNormalField(item, {}, data);
        
    //  Try rendering the new element using any of the default categories
    item_handled = false;
    for (var category in formElements)
    {
        if (item in formElements[category])
        {
            $new_elem=renderNormalField(item, {}, data);
            if ($new_elem)
            {
                item_handled = true;
                break;
            }
        }
    }
	
	if (!item_handled) {
		//Custom field
		//First, get the options for this custom field
		var custom_field, curr_category;
		$.each(formElements, function(cat, flds){
			if(item in flds){
				custom_field=flds[item];
				curr_category=cat;
				return false; //break out
			}
		});
        
		//Fields that are required on the model must necessarily be required in the form
		if(custom_field['required'])
			data.required=true;
		if(custom_field['field_type']=='custom')
			$new_elem=renderCustomField(item, custom_field['field_options'], data);
		else{
			$new_elem=renderNormalField(custom_field['field_type'], custom_field['field_options'], data);
			data.attrs={}; //Setting attrs to empty, as everything except links should already by defined on the server
		}
		
		//Set options for linked instances if not defined previously
		model_instance_cache[curr_category]['selected_cat']=$('#main_cat_spec').val();
		if(model_instance_cache[curr_category]['selected_cat'] != 'automatic')
			model_instance_cache[curr_category]['selected_inst']=$('#cat_instance_sel').val();
		else
			model_instance_cache[curr_category]['selected_inst']="-1";
	}
	
	//Inserting field into preview area, and attaching data
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

/*
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
	data.parent_id=-1; //Useful for modifications
	data.attrs={};
	
	//Generic fields first
	if(item=="textField"){
		$new_elem=$('<input/>', {
			type:"text",
			name:html_name,
			id:html_id,
			size:"30"
		});
		var key;
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
	}
	else if(item=="longTextField"){
		$new_elem=$('<input/>', {
			type:"text",
			name:html_name,
			id:html_id,
			size:"60"
		});
		var key;
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
	}
	else if(item=="longAns") {
		$new_elem=$('<textarea>', {
			name:html_name,
			id:html_id,
			rows:"8",
			cols:"50"
		});
		var key;
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
	}
	else if(item=="reallyLongAns") {
		$new_elem=$('<textarea>', {
			name:html_name,
			id:html_id,
			rows:"14",
			cols:"70"
		});
		var key;
		if($('#charOrWord').val()=='chars')
			key='charlimits';
		else key='wordlimits';	
		data['attrs'][key]=$('#text_min').attr('value') + ',' + $('#text_max').attr('value');
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
		$page_break.dblclick(function(){
			$currPage=$(this).next('div.form_preview'); 
			//$currSection=$(this).children(":last").children("div.section");
		}).toggle(function(){$(this).next('div.form_preview').children(".wrapper_button").addClass("wrapper_button_hover");}, 
				function(){$(this).next('div.form_preview').children(".wrapper_button").removeClass("wrapper_button_hover");}
				).appendTo($('div.preview_area'));
		
		//Now putting in the page div
		$currPage=$('<div class="form_preview"></div>');
		$currSection=$('<div class="section"></div>');
		$currPage.append($('<div class="outline"></div>').append($currSection));
		$('<input/>',{type:'button',value:'X'}).click(removeField).addClass("wrapper_button").appendTo($currPage);
		$currPage.toggle( function(){$(this).children(".wrapper_button").addClass("wrapper_button_hover");}, 
						function(){$(this).children(".wrapper_button").removeClass("wrapper_button_hover");});
		$currPage.dblclick(function(){
			$currPage=$(this);
			//$currSection=$(this).children(":last").children("div.section");
		});
		$currPage.appendTo($('div.preview_area'));
		$.data(($currSection.parent())[0], 'data', {'question_text':'', 'help_text':'', 'parent_id':-1});
		$.data($currPage[0], 'data', {'parent_id':-1});
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
*/

var submit=function() {
	//submits the created form to the server
	
	var form={'title':$('#form_title').html(), 'desc':$('#form_description').html(), 'anonymous':$('#id_anonymous').attr('checked'), 'pages':[]}, section, elem, page, section_seq, page_seq=0;
	form['link_type']=$('#links_id_main').val();
	if(form['link_type']!='-1' && $('#links_id_specify').val()=='particular')
		form['link_id']=$('#links_id_pick').val();
	else form['link_id']=-1;	
	
	form['success_message']=$('#input_form_sucmsg').val();
    form['success_url']=$('#input_suc_url').val();
	var form_perms='';
	if($('#id_main_perm').val()!='none'){
		form_perms+=$('#id_main_perm').val();
		if(!('#id_perm_program').is(':hidden'))
			form_perms+=","+$('#id_perm_program').val();
		if(!$('#id_sub_perm').is(':hidden'))
			form_perms+=","+$('#id_sub_perm').val();
	}
	form['perms']=form_perms;
	
	//Constructing the object to be sent to the server
	$('div.preview_area').children('div.form_preview').each(function(pidx,pel) {
		page={'sections':[], 'parent_id':$.data(pel, 'data')['parent_id'], 'seq':page_seq};
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
                    
					if(!inDefaultCategory(elem['data']['field_type'])){
						//Set link_id for link fields
						//First, figure out the category
						var curr_cat;
						$.each(formElements, function(cat, flds){
							if(elem['data']['field_type'] in flds){
								curr_cat=cat;
								return false
							}
						});
						elem['data']['attrs']['link_id']=model_instance_cache[curr_cat]['selected_inst'];
					}
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
		if(page['sections'].length!=0){
			form['pages'].push(page);
			page_seq++;
		}	
	});
	if(form['pages'].length==0){
		alert("Sorry, that's an empty form.");
		return;
	}
	console.log(form);
	//POSTing to server
	var post_url='/customforms/submit/';
	if($('#id_modify').attr('checked')){
		form.form_id=parseInt($('#base_form').val());
		post_url='/customforms/modify/';
	}
	$.ajax({
		url:post_url,
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
	/*$currPage=$('<div class="form_preview"></div>');
	$currSection=$('<div class="section"></div>');
	$currPage.append($('<div class="outline"></div>').append($currSection));
	$('div.preview_area').append($currPage);
	$.data($currPage[0], 'data', {'parent_id':-1});*/
	
	var base_form_id=$('#base_form').val();
	if(base_form_id!="-1"){
		$.ajax({
			url:'/customforms/metadata/',
			data:{'form_id':base_form_id},
			type:'GET',
			dataType:'json',
			async:false,
			success: function(metadata) {
				rebuild(metadata);
			}
		});
		$('#id_modify_wrapper').show();
	}
	else {
		$('#id_modify_wrapper').hide();
		$('#id_modify').attr('checked', false);
		$('#input_form_title').attr('value', '').change();
		$('#input_form_description').attr('value','').change();
		$('#id_anonymous').attr('checked', false);
	}
};

var rebuild=function(metadata) {
	//Takes form metadata, and reconstructs the form from it
	
	$('#outline_0').remove();
	//Setting form's title and description
	$('#input_form_title').attr('value', metadata['title']).change();
	$('#input_form_description').attr('value',metadata['desc']).change();
	console.log(metadata);
	//Setting other form options
	if(metadata['anonymous'])
		$('#id_anonymous').attr('checked', true);
	//Setting fkey-only links
	$('#links_id_main').val(metadata['link_type']);
	console.log($('#links_id_main').val());
	onChangeMainLink();
	if(metadata['link_id']!=-1){
		$('#links_id_specify').val('particular');
		onChangeLinksSpecify();
		$('#links_id_pick').val(metadata['link_id']);
	}
	else $('#links_id_specify').val('userdef');
	
	//Putting in pages, sections and fields
	$.each(metadata['pages'], function(pidx, page){
		addElement('page',[]);
		$.data($currPage[0], 'data')['parent_id']=page[0][0]['section__page__id'];
			
		$.each(page, function(sidx, section){
			$('#id_question').val(section[0]['section__title']);
			$('#id_instructions').val(section[0]['section__description']);
			var $outline=addElement('section',[]);
			$.data($outline[0], 'data')['parent_id']=section[0]['section__id'];
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
				
				if($.inArray(field['attribute__attr_type'], ['options', 'limits', 'link_id', 'charlimits', 'wordlimits'])!=-1)
					field_data.attrs[field['attribute__attr_type']]=field['attribute__value'];	
				//Checking for link fields
				var category=getFieldCategory(field_data['field_type']);
				if(category!='Generic' && category!='Personal' && category!='NotReallyFields') {
					$('#cat_selector').val(category);
					if(field_data.attrs['link_id']=="-1"){
						$('#main_cat_spec').val('automatic');
						onChangeMainCatSpec();
					}
					else {
						$('#main_cat_spec').val('particular');
						onChangeMainCatSpec();
						$('#cat_instance_sel').val(field_data.attrs['link_id']);
					}
				}
				onSelectField([], field_data);		
				$prevField=addElement(field['field_type'], $prevField);
				$.data($prevField[0], 'data')['parent_id']=field['id'];	
			});
		});
	});	
	
};

