/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.Queue");

function getQ(){
	var a = ["foo","bar","test","bull"];
	return new dojo.collections.Queue(a);
}

function test_Queue_ctor(){ 
	var queue = getQ();
	jum.assertEquals("test10", 4, queue.count);

}
function test_Queue_clear(){ 
	var queue = getQ();
	queue.clear();
	jum.assertEquals("test60", 0, queue.count);
}
function test_Queue_clone(){ 
	var queue = getQ();
	var cloned = queue.clone();
	jum.assertEquals("Queue.clone()", queue.count, cloned.count);
}
function test_Queue_contains(){ 
	var queue = getQ();
	jum.assertEquals("Queue.contains() 1", true, queue.contains("bar"));
	jum.assertEquals("Queue.contains() 2", false, queue.contains("faz"));
}
function test_Queue_getIterator(){ 
	var queue = getQ();
	var e = queue.getIterator();
	while(!e.atEnd()) e.get();
	jum.assertEquals("Queue.getIterator()", "bull", e.element);
}
function test_Queue_peek(){ 
	var queue = getQ();
	jum.assertEquals("Queue.peek()", "foo", queue.peek());
}
function test_Queue_dequeue(){ 
	var queue = getQ();
	jum.assertEquals("Queue.dequeue()", "foo", queue.dequeue());
}
function test_Queue_enqueue(){ 
	var queue = getQ();
	queue.enqueue("bull");
	var arr = queue.toArray();
	jum.assertEquals("Queue.enqueue()", "bull", arr[arr.length-1]);
}
function test_Queue_toArray(){ 
	var queue = getQ();
	var arr = queue.toArray();
	jum.assertEquals("Queue.toArray()", "foo,bar,test,bull" , arr.join(","));
}
