/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.ns");

function test_ns_Resolver(){
	
	var testResolver = function(name){
		var module = "test.ns."+dojo.string.capitalize(name);
		return module;
	};
	
	var ns=new dojo.ns.Ns("testx", "test.ns", testResolver);
	
	try {
		jum.assertFalse(ns.resolve("NonExistant"));
	} catch (e) { 
		jum.assertTrue(e instanceof Error);
		jum.assertTrue(e.message.indexOf("not found after loading") > -1);
		return;
	}
	throw new JUMAssertFailure("Previous test should have failed.");
}
