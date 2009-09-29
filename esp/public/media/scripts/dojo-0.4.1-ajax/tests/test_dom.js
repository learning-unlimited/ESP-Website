/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.dom");

function test_dom_sanityCheck(){
	var td = document.createElement("div");
	td.appendChild(document.createTextNode("foo"));
	td.appendChild(document.createCDATASection("bar"));
	var td2 = document.createElement("div");
	td.appendChild(td2);
	jum.assertEquals("test1", 3, td.childNodes.length);
}

function test_dom_getUniqueId(){ 
	var td = document.createElement("div");
	td.setAttribute("id", "dj_unique_1");    
    document.body.appendChild(td);
	jum.assertEquals("test40", "dj_unique_2", dojo.dom.getUniqueId());
}

function test_dom_getFirstChildElement(){
	var td = document.createElement("div");
	td.appendChild(document.createTextNode("foo"));
	td.appendChild(document.createCDATASection("bar"));
	var td2 = document.createElement("div");
	td.appendChild(td2);
	jum.assertTrue("test50", dojo.dom.getFirstChildElement(td) === td2);
}

function test_dom_getLastChildElement(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	td.appendChild(td2);
	td.appendChild(document.createTextNode("foo"));
	td.appendChild(document.createCDATASection("bar"));
	jum.assertTrue("test60", dojo.dom.getLastChildElement(td) === td2);
}

function test_dom_getNextSiblingElement(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	td.appendChild(td2);
	td.appendChild(document.createTextNode("foo"));
	var td3 = document.createElement("div");
	td.appendChild(td3);
	td.appendChild(document.createCDATASection("bar"));
	jum.assertTrue("test70", dojo.dom.getNextSiblingElement(td2) === td3);
	jum.assertTrue("test71", dojo.dom.nextElement(td2) === td3);
	jum.assertTrue("test80", dojo.dom.getNextSiblingElement(td3) === null);
	jum.assertTrue("test81", dojo.dom.nextElement(td3) === null);
}

function test_dom_getPreviousSiblingElement(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	td.appendChild(td2);
	td.appendChild(document.createTextNode("foo"));
	var td3 = document.createElement("div");
	td.appendChild(td3);
	td.appendChild(document.createCDATASection("bar"));
	jum.assertTrue("test90", dojo.dom.getPreviousSiblingElement(td3) === td2);
	jum.assertTrue("test91", dojo.dom.prevElement(td3) === td2);
	jum.assertTrue("test100", dojo.dom.getPreviousSiblingElement(td2) === null);
	jum.assertTrue("test101", dojo.dom.prevElement(td2) === null);
}

function test_dom_moveChildrenNoTrim(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	var td3 = document.createElement("div");
	td.appendChild(td2);
	td.appendChild(document.createTextNode("foo"));
	td.appendChild(td3);
	td.appendChild(document.createCDATASection("bar"));
	var ts = document.createElement("span");
	var moved = dojo.dom.moveChildren(td, ts, false);
	jum.assertEquals("test110", 4, moved);
	jum.assertEquals("test120", 4, ts.childNodes.length);
	jum.assertEquals("test130", 0, td.childNodes.length);
	jum.assertFalse("test140", td.hasChildNodes());
}

function test_dom_moveChildrenWithTrim(){
	// FIXME: this method is very weird. It only seems to trim text nodes and
	// not CDATA sections or other non-printing node types, but I'm not sure if
	// it's a bug in the method or my understanding of it
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	var td3 = document.createElement("div");
	td.appendChild(td2);
	td.appendChild(document.createTextNode("foo"));
	td.appendChild(td3);
	td.appendChild(document.createCDATASection("bar"));
	td.appendChild(document.createTextNode("baz"));
	var ts = document.createElement("span");
	var moved = dojo.dom.moveChildren(td, ts, true);
	jum.assertEquals("test150", 4, moved);
	jum.assertEquals("test160", 4, ts.childNodes.length);
	jum.assertEquals("test170", 0, td.childNodes.length);
	jum.assertFalse("test180", td.hasChildNodes());
}

function test_dom_copyChildren(){
	// FIXME: we can't test this now since JsFakeDom doesn't have an
	// implementation of cloneNode()
}

function test_dom_removeChildren(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	var td3 = document.createElement("div");
	td.appendChild(td2);
	td.appendChild(document.createTextNode("foo"));
	td.appendChild(td3);
	td.appendChild(document.createCDATASection("bar"));
	td.appendChild(document.createTextNode("baz"));
	var count = dojo.dom.removeChildren(td);
	jum.assertEquals("test190", 5, count);
	jum.assertEquals("test200", 0, td.childNodes.length);
	jum.assertFalse("test210", td.hasChildNodes());
}

function test_dom_replaceChildren(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	td.appendChild(td2);
	var nc = document.createTextNode("foo")
	dojo.dom.replaceChildren(td, nc);
	jum.assertEquals("test220", 1, td.childNodes.length);
	jum.assertTrue("test230", td.hasChildNodes());
	jum.assertTrue("test240", td.firstChild === nc);
}

function test_dom_removeNode(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	dojo.dom.removeChildren(document.body);
	jum.assertFalse("test250", document.body.hasChildNodes());
	document.body.appendChild(td2);
	jum.assertTrue("test260", document.body.hasChildNodes());
	var r1 = dojo.dom.removeNode(td);
	jum.assertTrue("test270", r1 == null);
	var r2 = dojo.dom.removeNode(td2);
	jum.assertTrue("test280", r2 === td2);
	jum.assertFalse("test290", document.body.hasChildNodes());
}

function test_dom_getAncestors(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	document.body.appendChild(td);
	td.appendChild(td2);
	var t2a = dojo.dom.getAncestors(td2);
	jum.assertTrue("test300", t2a[0] === td2);
	jum.assertTrue("test310", t2a[1] === td);
	jum.assertTrue("test320", t2a[2] === document.body);
	document.body.appendChild(td2);
	t2a = dojo.dom.getAncestors(td2);
	jum.assertTrue("test330", t2a[0] === td2);
	jum.assertTrue("test340", t2a[1] === document.body);
}

function test_dom_isDescendantOf(){
	var td = document.createElement("div");
	var td2 = document.createElement("div");
	document.body.appendChild(td);
	td.appendChild(td2);
	jum.assertTrue("test350", dojo.dom.isDescendantOf(td2, td));
	jum.assertTrue("test360", dojo.dom.isDescendantOf(td2, document.body));
	jum.assertTrue("test370", dojo.dom.isDescendantOf(td2, td2));
	jum.assertFalse("test380", dojo.dom.isDescendantOf(td2, td2, true));
}

function test_dom_innerXML(){
	// FIXME: we can't test this since there's no XMLSerializer instance in
	// JsFakeDom...
}

function test_dom_createDocumentFromText(){
	// FIXME: ...same goes for DOMParser
}


// FIXME:
//	still need to add tests for:
//		* insertBefore
//		* insertAfter
//		* insertAtPosition
//		* insertAtIndex
//		* textContent
//		* collectionToArray
