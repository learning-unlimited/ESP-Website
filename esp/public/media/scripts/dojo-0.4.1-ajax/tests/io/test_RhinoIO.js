/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

//Unccomment if not using unit test framework
//djConfig = { debug: true };
//load("dojo.js");

dojo.require("dojo.io.*");
dojo.require("dojo.io.RhinoIO");


function test_RhinoIO_get(){
	jum.debug("STARTING RHINO IO TEST");
	dojo.io.bind({
		/* test GET */
		url: "http://search.yahoo.com/search?",
		method: "get",
		content: {
			p: "aoeu"
		},
	
		/* test POST w/ content */
		/*
		url: "http://www.snee.com/xml/crud/posttest.cgi",
		method: "post",
		content: {
			fname: "David",
			lname: "Snopek"
		},
		*/
	
		/* test POST w/ postContent */
		/*
		url: "http://www.snee.com/xml/crud/posttest.cgi",
		method: "post",
		postContent: "I AM POST",
		*/
		
		/* Standard stuff */
		sync: true,
		load: function (type, data) { jum.assertTrue("Rhino IO LOAD FAILED: " + data, data != null); },
		error: function (type, data) { jum.assertFalse("Error: " + data, data != null) },
		//handle: function (type, data) { },
		timeout: function (type, data) { jum.assertFalse("Timeout error.", true) },
		timeoutSeconds: 20,
		mimetype: "text/plain",
		transport: "RhinoHTTPTransport"
	});
	
	jum.debug("ENDING RHINO IO TEST");
}

//Unccomment if not using unit test framework
//test_RhinoIO_get();