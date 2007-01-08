/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.date.supplemental");

function test_date_isWeekend() {
	var thursday = new Date(2006, 8, 21);
	var friday = new Date(2006, 8, 22);
	var saturday = new Date(2006, 8, 23);
	var sunday = new Date(2006, 8, 24);
	var monday = new Date(2006, 8, 25);
	jum.assertFalse("isWeekend_test1", dojo.date.isWeekend(thursday, 'en-us'));
	jum.assertTrue("isWeekend_test2", dojo.date.isWeekend(saturday, 'en-us'));
	jum.assertTrue("isWeekend_test3", dojo.date.isWeekend(sunday, 'en-us'));
	jum.assertFalse("isWeekend_test4", dojo.date.isWeekend(monday, 'en-us'));
	jum.assertFalse("isWeekend_test5", dojo.date.isWeekend(saturday, 'en-in'));
	jum.assertTrue("isWeekend_test6", dojo.date.isWeekend(sunday, 'en-in'));
	jum.assertFalse("isWeekend_test7", dojo.date.isWeekend(monday, 'en-in'));
	jum.assertTrue("isWeekend_test8", dojo.date.isWeekend(friday, 'he-il'));
	jum.assertFalse("isWeekend_test9", dojo.date.isWeekend(sunday, 'he-il'));
}
