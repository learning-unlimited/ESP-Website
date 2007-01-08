/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.widget.Widget");

function test_widget_ctor(){
	jum.debug("in widget.ctor");
	var obj1 = new dojo.widget.Widget();

	jum.assertTrue("test1", typeof obj1 == "object");
//	jum.assertTrue("test2", obj1.widgetType == "Widget");
}
