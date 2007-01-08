/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.ArrayList");

function getAL(){
	return new dojo.collections.ArrayList(["foo","bar","test","bull"]);
}

function test_ArrayList_ctor(){
	var al = getAL();

	//	test the constructor
	jum.assertEquals("test10", 4, al.count);
}

function test_ArrayList_add(){
	var al = getAL();

	//	test add and addRange
	al.add("carp");
	jum.assertEquals("test20", "foo,bar,test,bull,carp", al.toString());

	al.addRange(["oof","rab"]);
	jum.assertEquals("test30", "foo,bar,test,bull,carp,oof,rab", al.toString());
}

function test_ArrayList_clear(){
	var al = getAL();
	al.clear();
	jum.assertEquals("test60", 0, al.count);
}

function test_ArrayList_clone(){
	//	clone
	var al = getAL();
	var cloned = al.clone();
	jum.assertEquals("test70", al.toString(), cloned.toString());
}

function test_ArrayList_contains(){
	var al = getAL();
	//	contains
	jum.assertEquals("test80", true, al.contains("bar"));
	jum.assertEquals("test90", false, al.contains("faz"));
}

function test_ArrayList_getIterator(){
	var al = getAL();
	//	iterator test
	var e = al.getIterator();
	while(!e.atEnd()){ 
		e.get(); 
	}
	jum.assertEquals("test100", "bull", e.element);
}

function test_ArrayList_indexOf(){
	var al = getAL();
	//	indexOf
	jum.assertEquals("test110", 1, al.indexOf("bar"));
}

function test_ArrayList_insert(){
	var al = getAL();
	// insert
	al.insert(2, "baz");
	jum.assertEquals("ArrayList.insert", 2, al.indexOf("baz"));
}

function test_ArrayList_item(){
	var al = getAL();
	// item
	jum.assertEquals("test130", "test", al.item(2));
}

function test_ArrayList_remove(){
	var al = getAL();
	// remove
	al.remove("bar");
	jum.assertEquals("test140", 3, al.count);
}

function test_ArrayList_removeAt(){
	var al = getAL();
	// removeAt
	al.removeAt(3);
	jum.assertEquals("test150", "foo,bar,test", al.toString());
}

function test_ArrayList_reverse(){
	var al = getAL();
	//	reverse
	al.reverse();
	jum.assertEquals("test160", "bull,test,bar,foo", al.toString());
}

function test_ArrayList_sort(){
	var al = getAL();
	// sort
	al.sort();
	jum.assertEquals("test170", "bar,bull,foo,test", al.toString());
}

function test_ArrayList_sort(){
	var al = getAL();
	//	toArray
	var a = al.toArray();
	jum.assertEquals("test180", a.join(","), al.toString());
}
