/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

//paramOne=one3333333333&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four&paramOne=one&paramTwo=two&paramThree=three&paramFour=four

function getPartNumber(url){
	var result = 0;
	var partMatch = url.match(/_part=(.*?)(&|$)/);
	if(partMatch){
		result = partMatch[1];
	}
	return result;
}

function getRequestId(url){
	var result = 'NO ID FOUND';
	var idMatch = url.match(/_dsrid=(.*?)(&|$)/);
	if(idMatch){
		result = idMatch[1];
	}
	return result;
}

var testMultipartStatusCodeContinue = 100;
var testMultipartStatusCodeOk = 200;

function foundPart(){
	var result = false;
	var part = 0;
	var currentPart, partMatch, partMethod;
	var scriptUrls = getScriptUrls();

	var shouldDoServerParamChange = false;
	for(var i = 0; i < scriptUrls.length; i++){
		currentPart = getPartNumber(scriptUrls[i]);
		if(currentPart != 0 && currentPart > part){
			part = currentPart;
			if(scriptUrls[i].match(/TESTSERVERPARAMCHANGE\=TRUE/)){
				shouldDoServerParamChange = true;
			}else{
				shouldDoServerParamChange = false;
			}
			result = true;
		}
	}

	if(result){
		document.getElementById('output').innerHTML += 'Calling onscriptload with part #' + part + '<br>';

		var constantParams = null;
		if(shouldDoServerParamChange){
			constantParams = 'SERVERPARAM1=one&SERVERPARAM2=two&SERVERPARAM3=three';
		}
		window.onscriptload({
			id: getRequestId(scriptUrls[0]),
			status: testMultipartStatusCodeContinue,
			statusText: 'Continue',
			response: { part: part, constantParams: constantParams }
		});
	}

	return result;	
}

function findDone(){
	var result = false;
	var scriptUrls = getScriptUrls();

	for(var i = 0; i < scriptUrls.length; i++){
		if(getPartNumber(scriptUrls[i]) == 0){
			window.onscriptload({
				id: getRequestId(scriptUrls[i]),
				status: testMultipartStatusCodeOk,
				statusText: 'OK',
				response: scriptUrls.join('\n').replace(/\'/g, "\\'")
			});
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

function doCallback(){
	if(!findDone()){ //If didn't find an URL without a part, then we must be in a part.
		if(!foundPart()){ //If didn't find a part, then we are hosed.
			alert('ERROR: Could not find a part, or final request.');
		}
	}
}

//Set a timeout to do the callback check, since MSIE won't see the SCRIPT tag until
//we complete processing of this page.
setTimeout('doCallback()', 300);
