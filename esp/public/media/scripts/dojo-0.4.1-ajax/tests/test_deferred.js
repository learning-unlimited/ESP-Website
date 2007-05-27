/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.logging.Logger");
dojo.require("dojo.Deferred");

function test_Deferred_Callback(){
	var d=new dojo.Deferred();
	d.addCallback(deferredCallback);
	
	setTimeout(function(){d.callback("Test message");}, 100);
}

function deferredCallback(msg){
	dojo.log.debug("deferredCallback called with " + msg);
	jum.assertTrue("defcallback", true);	
}
