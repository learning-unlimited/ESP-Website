/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.provide("tests.widget.namespaces.myns.manifest");
dojo.require("dojo.string.extras");

// This is a full custom namespace example
// By convention, myns lives in <dojo root>/../myns/, 
// and myns widgets are in myns.widget
// Convention paths are autodiscovered, and all we would 
// have to do here is register a resolver with 
// dojo.registerNamespaceResolver("myns", <resolver>);

dojo.registerNamespaceManifest("myns", "tests/widget/namespaces/myns", "myns", "myns.widget",
	function(name){
		var module = "myns.widget."+dojo.string.capitalize(name);
		dojo.debug("resolver returning '"+module+"' for '"+name+"'"); 
		return module;
	}
);

