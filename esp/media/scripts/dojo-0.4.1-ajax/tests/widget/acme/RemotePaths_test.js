/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

// needed in test_RemotePaths.html
// needs executescripts true
	obj.extScriptToggle = function(){
		var a = document.getElementById("extToggler");
		var txt = a.firstChild.nodeValue;
		if(txt == "Ext. js file scripttest, Released"){
			txt = "Ext. js file scripttest, Pushed";
		}else{
			txt = "Ext. js file scripttest, Released";
		}
		var txtNode = document.createTextNode(txt);
		a.replaceChild(txtNode,a.firstChild);
	}