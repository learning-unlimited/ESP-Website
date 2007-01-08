/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.SortedList");

function getSL(){
	return new dojo.collections.SortedList();
}

function test_SortedList_ctor(){
	var sl = getSL();
	jum.assertEquals("SortedList.ctor", (sl instanceof dojo.collections.SortedList) , true);
}

function test_SortedList_add(){ 
	var sl = getSL();
	sl.add("foo","bar");
	jum.assertEquals("SortedList.add", "bar" , sl.item("foo").valueOf());
}
function test_SortedList_clear(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.clear();
	jum.assertEquals("SortedList.clear", 0, sl.count);
}
function test_SortedList_clone(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	var d2 = sl.clone();
	jum.assertEquals("SortedList.clone", true, d2.contains("baz"));
}
function test_SortedList_contains(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.contains", true, sl.contains("baz"));
}
function test_SortedList_containsKey(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.containsKey", true, sl.containsKey("buck"));
}
function test_SortedList_containsValue(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.containsValue", true, sl.containsValue("shot"));
}
function test_SortedList_getKeyList(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	var keys = sl.getKeyList();
	jum.assertEquals("SortedList.getKeyList", "foo,baz,buck,apple", keys.join(","));
}
function test_SortedList_getValueList(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	var values = sl.getValueList();
	jum.assertEquals("SortedList.getValueList", "bar,fab,shot,orange", values.join(","));
}
function test_SortedList_copyTo(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	var arr = ["bek"];
	sl.copyTo(arr,0);
	jum.assertEquals("SortedList.copyTo", "bar,fab,shot,orange,bek", arr.join(","));
}
function test_SortedList_getByIndex(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.getByIndex", "shot", sl.getByIndex(2));
}
function test_SortedList_getKey(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.getKey", "apple", sl.getKey(0));
}
function test_SortedList_indexOfKey(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.indexOfKey", 0, sl.indexOfKey("apple"));
}
function test_SortedList_indexOfValue(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	jum.assertEquals("SortedList.indexOfValue", 3, sl.indexOfValue("bar"));
}
function test_SortedList_remove(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	sl.remove("baz");
	jum.assertEquals("SortedList.remove test1", 3, sl.count);
	jum.assertEquals("SortedList.remove test2", undefined, sl.item("baz"));
}
function test_SortedList_removeAt(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	sl.removeAt(2);
	jum.assertEquals("SortedList.removeAt", undefined, sl.item("buck"));
}
function test_SortedList_setByIndex(){ 
	var sl = getSL();
	sl.add("foo","bar");
	sl.add("baz","fab");
	sl.add("buck","shot");
	sl.add("apple","orange");
	sl.setByIndex(0, "bar");
	jum.assertEquals("SortedList.setByIndex", "bar", sl.getByIndex(0));
}
