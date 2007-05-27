/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.registerModulePath("tests", "tests");
dojo.require("tests.MockXMLHttpRequest");
dojo.require("dojo.io.*");
	
var testTimerCalled = false;
var testBindJson = null;

function test_MockXMLHttpRequest(){	
	if (dojo.hostenv.name_ == 'browser') {
		//test basic functionality using dojo.hostenv.getText
		//(only test on environments that implement getText with XHR)
		var responseText = "this is a test!";
		tests.MockXMLHttpRequest.set(responseText, 1000); //simulate a 1 sec response time
		dojo.hostenv.getText('urn:this_is_ignored', 
					function(data) {
						jum.assertTrue(data == responseText);
						jum.assertTrue(testTimerCalled);									 								
					});
		tests.MockXMLHttpRequest.restore(); 
		setTimeout(function() { testTimerCalled = true; }, 200);
	}
	
	//test dojo.io.bind
	tests.MockXMLHttpRequest.set('[10]', 100);	
	dojo.io.bind({
		url: "http://ignore",
		method: "get",
		mimetype: "text/json",
		handle: function(type, data, evt) {
			if(type == "load"){
				testBindJson = data;										
			}
		}
	});
	setTimeout(function() { jum.assertTrue('async io completed', 
		testBindJson && testBindJson[0] == 10);}, 500);
	 
	//test abort()	
	tests.MockXMLHttpRequest.set('test abort', 500);
	bindKw = {
		url: "http://ignore2",
		method: "get",
		mimetype: "text/plain" ,
		handle: function(type, data, evt) {
			jum.assertTrue("bind.abort didn't work", false);
		}
	}
	var request = dojo.io.bind(bindKw);
	request.abort();
	
	//test post
	tests.MockXMLHttpRequest.set(function(xhr) { return xhr.data; }, 100);
	var postData = "test post data";
	dojo.io.bind({
		url: "http://ignore", 
		method: "post",
		postContent: postData,
		mimetype: "text/plain",
		handle: function(type, data, evt) {
			jum.assertTrue("receive post data", type == "load" && data == postData);
		}
	});
	
	//test sync
	//(note: response time doesn't work with sync)
	var testSyncData = '';
	dojo.io.bind({
		sync: true,
		url: "http://ignore", 
		method: "post",
		postContent: postData,
		mimetype: "text/plain",
		handle: function(type, data, evt) {
			if(type == "load"){
				testSyncData = data;
			} else {
				dojo.debug('mock request problem: ' + type + ' ' + dojo.json.serialize(data));
			}
		}
	});
	//handle func should be called immediately 
	jum.assertTrue("test sync", testSyncData == postData); 

	tests.MockXMLHttpRequest.restore(); 
	
	//test tests.MockXMLHttpRequest.wrap
	var responseText = "this is a test!";
	tests.MockXMLHttpRequest.wrap(dj_global, 'wrapMockRequestTest', responseText, 50);
	jum.assertFalse( wrapMockRequestTest() );
	//the wrapping should only happen once
	jum.assertTrue( wrapMockRequestTest() );
}

function wrapMockRequestTest() {
	return dojo.hostenv.getXmlhttpObject == tests.MockXMLHttpRequest._originalXmlhttpObjectGetter;
}