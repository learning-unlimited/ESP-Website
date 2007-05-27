/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.event.*");

function topicTestClass(){
	this.testVal = 0;

	this.testPublish = function(){
		this.testVal = 1;
	}

	this.testSubscribe = function(val){
		this.testVal = (val) ? val : 2;
	}
}

function test_topic_registerPublisher(){
	var tobj = new topicTestClass();
	dojo.event.topic.registerPublisher("/test", tobj, "testPublish");
	jum.assertEquals("test 10", "object", (typeof dojo.event.topic.topics["/test"]));
	// get a reference to the join-point object for our testPublish method. If
	// connection happened correctly, then the topic object will have requested
	// to be notified when an event is thrown. This shows up as an entry in the
	// "after" advice property of the join point ojbect.
	var mjp = dojo.event.MethodJoinPoint.getForMethod(tobj, "testPublish");
	jum.assertEquals("test 20", 1, mjp.after.length);
	jum.assertTrue("test 20", (mjp.after[0] instanceof Array));
	jum.assertEquals("test 30", 7, mjp.after[0].length);

	dojo.event.topic.subscribe("/test", tobj, "testSubscribe");
	tobj.testPublish();
	jum.assertEquals("test 40", 2, tobj.testVal);
}

function test_topic_getTopic(){
	var test2topic = dojo.event.topic.getTopic("/test2");
	jum.assertTrue("test 50", (test2topic instanceof dojo.event.topic.TopicImpl));
}

function test_topic_publish(){
	var tobj = new topicTestClass();
	dojo.event.topic.subscribe("/test3", tobj, "testSubscribe");
	dojo.event.topic.publish("/test3", "foo");
	jum.assertEquals("test 60", "foo", tobj.testVal);
}

function test_topic_subscribe(){
	var tobj = new topicTestClass();
	dojo.event.topic.subscribe("/test4", tobj, "testSubscribe");
	dojo.event.topic.publish("/test4", "bar");
	jum.assertEquals("test 70", "bar", tobj.testVal);
}

function test_topic_unsubscribe(){
	var tobj = new topicTestClass();
	dojo.event.topic.subscribe("/test5", tobj, "testSubscribe");
	dojo.event.topic.publish("/test5", "foo");
	dojo.event.topic.unsubscribe("/test5", tobj, "testSubscribe");
	dojo.event.topic.publish("/test5", "bar");
	jum.assertEquals("test 80", "foo", tobj.testVal);
}

function test_topic_permissiveSubscribe(){
	var foo = "bar";
	var tf = function(){ foo = "baz"; };
	dojo.event.topic.subscribe("/test6", tf);
	dojo.event.topic.publish("/test6", "bar");
	jum.assertEquals("test 90", "baz", foo);
}

function test_topic_destroy(){
	var tobj = new topicTestClass();
	dojo.event.topic.subscribe("/test5", tobj, "testSubscribe");
	dojo.event.topic.publish("/test5", "foo");
	dojo.event.topic.destroy("/test5");
	dojo.event.topic.publish("/test5", "bar");
	jum.assertEquals("test 80", "foo", tobj.testVal);
}
