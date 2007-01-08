/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

function getJsonpCallback(url){
	var result = null;
	var idMatch = url.match(/jsonp=(.*?)(&|$)/);
	if(idMatch){
		result = idMatch[1];
	}else{
		//jsonp didn't match, so maybe it is the jsonCallback thing.
		idMatch = url.match(/callback=(.*?)(&|$)/);
		if(idMatch){
			result = idMatch[1];
		}
	}
	
	if(result){
		result = decodeURIComponent(result);
	}
	return result;
}

function findJsonpDone(){
	var result = false;
	var scriptUrls = getScriptUrls();
	
	for(var i = 0; i < scriptUrls.length; i++){
		var jsonp = getJsonpCallback(scriptUrls[i]);
		if(jsonp){
			eval(jsonp + "({animalType: 'mammal'});");
			result = true;
			break;
		}
	}
	return result;
}

function getScriptUrls(){
	//Get the script tags in the page to figure what state we are in.
	var scripts = document.getElementsByTagName('script');
	var scriptUrls = new Array();
	for(var i = 0; scripts && i < scripts.length; i++){
		var scriptTag = scripts[i];
		if(scriptTag.className == 'ScriptSrcTransport'){
			scriptUrls.push(scriptTag.src);
		}
	}

	return scriptUrls;
}

function doJsonpCallback(){
	if(!findJsonpDone()){
		 alert('ERROR: Could not jsonp callback!');
	}
}

//Set a timeout to do the callback check, since MSIE won't see the SCRIPT tag until
//we complete processing of this page.
setTimeout('doJsonpCallback()', 300);
