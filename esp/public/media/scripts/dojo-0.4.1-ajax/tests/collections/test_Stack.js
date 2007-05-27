/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.Stack");
function getStack(){
	var a = ["foo","bar","test","bull"];
	return new dojo.collections.Stack(a);
}

function test_Stack_ctor(){ 
	var stack = getStack();
	jum.assertEquals("test10", 4, stack.count);

}
function test_Stack_clear(){ 
	var stack = getStack();
	stack.clear();
	jum.assertEquals("test60", 0, stack.count);
}
function test_Stack_clone(){ 
	var stack = getStack();
	var cloned = stack.clone();
	jum.assertEquals("Stack.clone()", stack.count, cloned.count);
}
function test_Stack_contains(){ 
	var stack = getStack();
	jum.assertEquals("Stack.contains() 1", true, stack.contains("bar"));
	jum.assertEquals("Stack.contains() 2", false, stack.contains("faz"));
}
function test_Stack_getIterator(){ 
	var stack = getStack();
	var e = stack.getIterator();
	while (!e.atEnd()) e.get();
	jum.assertEquals("Stack.getIterator()", "bull", e.element);
}
function test_Stack_peek(){ 
	var stack = getStack();
	jum.assertEquals("Stack.peek()", "bull", stack.peek());
}
function test_Stack_pop(){ 
	var stack = getStack();
	jum.assertEquals("Stack.pop() 1", "bull", stack.pop());
	jum.assertEquals("Stack.pop() 2", "test", stack.pop());
}
function test_Stack_push(){ 
	var stack = getStack();
	stack.push("bull");
	jum.assertEquals("Stack.push()", "bull", stack.peek());
}
function test_Stack_toArray(){ 
	var stack = getStack();
	var arr = stack.toArray();
	jum.assertEquals("Stack.toArray()", "foo,bar,test,bull" , arr.join(","));
}
