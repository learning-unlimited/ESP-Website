/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.Dictionary");

function getDict(){
	return new dojo.collections.Dictionary();
}

function test_Dictionary_ctor(){ 
	var d=getDict();
	jum.assertEquals("Dictionary:ctor", (d instanceof dojo.collections.Dictionary), true);
}
function test_Dictionary_add(){ 
	var d=getDict();
	d.add("foo","bar");
	jum.assertEquals("Dictionary.add", "bar" , d.item("foo").valueOf());
}
function test_Dictionary_clear(){ 
	var d=getDict();
	d.add("foo","bar");
	d.clear();
	jum.assertEquals("Dictionary.clear", 0, d.count);
}
function test_Dictionary_clone(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	var d2 = d.clone();
	jum.assertEquals("Dictionary.clone", true, d2.contains("baz"));
}
function test_Dictionary_contains(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	jum.assertEquals("Dictionary.contains", true, d.contains("baz"));
}
function test_Dictionary_containsKey(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	jum.assertEquals("Dictionary.containsKey", true, d.containsKey("buck"));
}
function test_Dictionary_containsValue(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	jum.assertEquals("Dictionary.containsValue", true, d.containsValue("shot"));
}
function test_Dictionary_getKeyList(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	var keys = d.getKeyList();
	jum.assertEquals("Dictionary.getKeyList", "foo,baz,buck,apple", keys.join(","));
}
function test_Dictionary_getValueList(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	var values = d.getValueList();
	jum.assertEquals("Dictionary.getValueList", "bar,fab,shot,orange", values.join(","));
}
function test_Dictionary_remove(){ 
	var d=getDict();
	d.add("foo","bar");
	d.add("baz","fab");
	d.add("buck","shot");
	d.add("apple","orange");
	d.remove("baz");
	jum.assertEquals("Dictionary.remove test1", 3, d.count);
	jum.assertEquals("Dictionary.remove test2", undefined, d.item("baz"));
}
