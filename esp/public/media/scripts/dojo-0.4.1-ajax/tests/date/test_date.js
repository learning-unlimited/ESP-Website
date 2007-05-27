/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.date.common");

/* Supplementary Date Functions
 *******************************/

function test_date_setDayOfYear () {
	jum.assertEquals("getDayOfYear_test1", 23, dojo.date.setDayOfYear(new Date(2006,0,1), 23).getDate());
}

function test_date_getDayOfYear () {
	jum.assertEquals("getDayOfYear_test1", 1, dojo.date.getDayOfYear(new Date(2006,0,1)));
	jum.assertEquals("getDayOfYear_test2", 32, dojo.date.getDayOfYear(new Date(2006,1,1)));
}



function test_date_setWeekOfYear () {
	//dojo.date.setWeekOfYear(new Date(2006,2,1), 34);
	//dojo.date.setWeekOfYear(new Date(2006,2,1), 34, 1);
}

function test_date_getWeekOfYear () {
	//dojo.date.getWeekOfYear(new Date(2006,1,1));
	//dojo.date.getWeekOfYear(new Date(2006,1,1), 1);
}




function test_date_setIsoWeekOfYear () {
	//dojo.date.setIsoWeekOfYear(new Date(2006,2,1), 34);
	//dojo.date.setIsoWeekOfYear(new Date(2006,2,1), 34, 1);
}

function test_date_getIsoWeekOfYear () {
	//dojo.date.getIsoWeekOfYear(new Date(2006,1,1));
	//dojo.date.getIsoWeekOfYear(new Date(2006,1,1), 1);
}



/* Informational Functions
 **************************/

function test_date_getDaysInMonth () {
	// months other than February
	jum.assertEquals("getDaysInMonth_test1", 31, dojo.date.getDaysInMonth(new Date(2006,0,1)));
	jum.assertEquals("getDaysInMonth_test2", 31, dojo.date.getDaysInMonth(new Date(2006,2,1)));
	jum.assertEquals("getDaysInMonth_test3", 30, dojo.date.getDaysInMonth(new Date(2006,3,1)));
	jum.assertEquals("getDaysInMonth_test4", 31, dojo.date.getDaysInMonth(new Date(2006,4,1)));
	jum.assertEquals("getDaysInMonth_test5", 30, dojo.date.getDaysInMonth(new Date(2006,5,1)));
	jum.assertEquals("getDaysInMonth_test6", 31, dojo.date.getDaysInMonth(new Date(2006,6,1)));
	jum.assertEquals("getDaysInMonth_test7", 31, dojo.date.getDaysInMonth(new Date(2006,7,1)));
	jum.assertEquals("getDaysInMonth_test8", 30, dojo.date.getDaysInMonth(new Date(2006,8,1)));
	jum.assertEquals("getDaysInMonth_test9", 31, dojo.date.getDaysInMonth(new Date(2006,9,1)));
	jum.assertEquals("getDaysInMonth_test10", 30, dojo.date.getDaysInMonth(new Date(2006,10,1)));
	jum.assertEquals("getDaysInMonth_test11", 31, dojo.date.getDaysInMonth(new Date(2006,11,1)));

	// Februarys
	jum.assertEquals("getDaysInMonth_test12", 28, dojo.date.getDaysInMonth(new Date(2006,1,1)));
	jum.assertEquals("getDaysInMonth_test13", 29, dojo.date.getDaysInMonth(new Date(2004,1,1)));
	jum.assertEquals("getDaysInMonth_test14", 29, dojo.date.getDaysInMonth(new Date(2000,1,1)));
	jum.assertEquals("getDaysInMonth_test15", 28, dojo.date.getDaysInMonth(new Date(1900,1,1)));
	jum.assertEquals("getDaysInMonth_test16", 28, dojo.date.getDaysInMonth(new Date(1800,1,1)));
	jum.assertEquals("getDaysInMonth_test17", 28, dojo.date.getDaysInMonth(new Date(1700,1,1)));
	jum.assertEquals("getDaysInMonth_test18", 29, dojo.date.getDaysInMonth(new Date(1600,1,1)));
}

function test_date_isLeapYear () {
	jum.assertFalse("isLeapYear_test1", dojo.date.isLeapYear(new Date(2006,0,1)));
	jum.assertTrue("isLeapYear_test2", dojo.date.isLeapYear(new Date(2004,0,1)));
	jum.assertTrue("isLeapYear_test3", dojo.date.isLeapYear(new Date(2000,0,1)));
	jum.assertFalse("isLeapYear_test4", dojo.date.isLeapYear(new Date(1900,0,1)));
	jum.assertFalse("isLeapYear_test5", dojo.date.isLeapYear(new Date(1800,0,1)));
	jum.assertFalse("isLeapYear_test6", dojo.date.isLeapYear(new Date(1700,0,1)));
	jum.assertTrue("isLeapYear_test7", dojo.date.isLeapYear(new Date(1600,0,1)));
}

// The getTimezone function pulls from either the date's toString or
// toLocaleString method -- it's really just a string-processing
// function (assuming the Date obj passed in supporting both toString 
// and toLocaleString) and as such can be tested for multiple browsers
// by manually settting up fake Date objects with the actual strings
// produced by various browser/OS combinations.
// FIXME: the function and tests are not localized.
function test_date_getTimezoneName() {
	
	// Create a fake Date object with toString and toLocaleString
	// results manually set to simulate tests for multiple browsers
	function fakeDate(str, strLocale) {
		this.str = str || '';
		this.strLocale = strLocale || '';
		this.toString = function() {
			return this.str;
		};
		this.toLocaleString = function() {
			return this.strLocale;
		};
	}
	var dt = new fakeDate();
	
	// FF 1.5 Ubuntu Linux (Breezy)
	dt.str = 'Sun Sep 17 2006 22:25:51 GMT-0500 (CDT)';
	dt.strLocale = 'Sun 17 Sep 2006 10:25:51 PM CDT';
	jum.assertEquals("getTimezoneName_test1", 'CDT', dojo.date.getTimezoneName(dt));

	// Safari 2.0 Mac OS X 10.4
	dt.str = 'Sun Sep 17 2006 22:55:01 GMT-0500';
	dt.strLocale = 'September 17, 2006 10:55:01 PM CDT';
	jum.assertEquals("getTimezoneName_test2", 'CDT', dojo.date.getTimezoneName(dt));

	// FF 1.5 Mac OS X 10.4
	dt.str = 'Sun Sep 17 2006 22:57:18 GMT-0500 (CDT)';
	dt.strLocale = 'Sun Sep 17 22:57:18 2006';
	jum.assertEquals("getTimezoneName_test3", 'CDT', dojo.date.getTimezoneName(dt));

	// Opera 9 Mac OS X 10.4 -- no TZ data expect empty string return
	dt.str = 'Sun, 17 Sep 2006 22:58:06 GMT-0500';
	dt.strLocale = 'Sunday September 17, 22:58:06 GMT-0500 2006';
	jum.assertEquals("getTimezoneName_test4", '', dojo.date.getTimezoneName(dt));
	
	// IE 6 Windows XP
	dt.str = 'Mon Sep 18 11:21:07 CDT 2006';
	dt.strLocale = 'Monday, September 18, 2006 11:21:07 AM';
	jum.assertEquals("getTimezoneName_test5", 'CDT', dojo.date.getTimezoneName(dt));

	// Opera 9 Ubuntu Linux (Breezy) -- no TZ data expect empty string return 
	dt.str = 'Mon, 18 Sep 2006 13:30:32 GMT-0500';
	dt.strLocale = 'Monday September 18, 13:30:32 GMT-0500 2006';
	jum.assertEquals("getTimezoneName_test6", '', dojo.date.getTimezoneName(dt));
	
	// IE 5.5 Windows 2000
	dt.str = 'Mon Sep 18 13:49:22 CDT 2006';
	dt.strLocale = 'Monday, September 18, 2006 1:49:22 PM';
	jum.assertEquals("getTimezoneName_test7", 'CDT', dojo.date.getTimezoneName(dt));
}

function test_date_getOrdinal () {
	jum.assertEquals("getOrdinal_test1", "st", dojo.date.getOrdinal(new Date(2006,0,1)));
	jum.assertEquals("getOrdinal_test2", "nd", dojo.date.getOrdinal(new Date(2006,0,2)));
	jum.assertEquals("getOrdinal_test3", "rd", dojo.date.getOrdinal(new Date(2006,0,3)));
	jum.assertEquals("getOrdinal_test4", "th", dojo.date.getOrdinal(new Date(2006,0,4)));
	jum.assertEquals("getOrdinal_test5", "th", dojo.date.getOrdinal(new Date(2006,0,11)));
	jum.assertEquals("getOrdinal_test6", "th", dojo.date.getOrdinal(new Date(2006,0,12)));
	jum.assertEquals("getOrdinal_test7", "th", dojo.date.getOrdinal(new Date(2006,0,13)));
	jum.assertEquals("getOrdinal_test8", "th", dojo.date.getOrdinal(new Date(2006,0,14)));
	jum.assertEquals("getOrdinal_test9", "st", dojo.date.getOrdinal(new Date(2006,0,21)));
	jum.assertEquals("getOrdinal_test10", "nd", dojo.date.getOrdinal(new Date(2006,0,22)));
	jum.assertEquals("getOrdinal_test11", "rd", dojo.date.getOrdinal(new Date(2006,0,23)));
	jum.assertEquals("getOrdinal_test12", "th", dojo.date.getOrdinal(new Date(2006,0,24)));
}


/* Date compare and add Functions
 *********************************/

function test_date_compare(){
	var d1=new Date();
	d1.setHours(0);
	var d2=new Date();
	d2.setFullYear(2005);
	d2.setHours(12);
	jum.assertEquals("compare_test1", 0, dojo.date.compare(d1, d1));
	jum.assertEquals("compare_test2", 1, dojo.date.compare(d1, d2, dojo.date.compareTypes.DATE));
	jum.assertEquals("compare_test3", -1, dojo.date.compare(d2, d1, dojo.date.compareTypes.DATE));
	jum.assertEquals("compare_test4", -1, dojo.date.compare(d1, d2, dojo.date.compareTypes.TIME));
	jum.assertEquals("compare_test5", 1, dojo.date.compare(d1, d2, dojo.date.compareTypes.DATE|dojo.date.compareTypes.TIME));
}

function test_date_add(){
	var interv = ''; // Interval (e.g., year, month)
	var dtA = null; // Date to increment
	var dtB = null; // Expected result date
	
	interv = dojo.date.dateParts.YEAR;
	dtA = new Date(2005, 11, 27);
	dtB = new Date(2006, 11, 27);
	jum.assertEquals("add_test1", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2005, 11, 27);
	dtB = new Date(2004, 11, 27);
	jum.assertEquals("add_test1a", dtB, dojo.date.add(dtA, interv, -1));
	
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2001, 1, 28);
	jum.assertEquals("add_test2", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2005, 1, 28);
	jum.assertEquals("add_test3", dtB, dojo.date.add(dtA, interv, 5));
	
	dtA = new Date(1900, 11, 31);
	dtB = new Date(1930, 11, 31);
	jum.assertEquals("add_test4", dtB, dojo.date.add(dtA, interv, 30));
	
	dtA = new Date(1995, 11, 31);
	dtB = new Date(2030, 11, 31);
	jum.assertEquals("add_test5", dtB, dojo.date.add(dtA, interv, 35));

	interv = dojo.date.dateParts.QUARTER;
	dtA = new Date(2000, 0, 1);
	dtB = new Date(2000, 3, 1);
	jum.assertEquals("add_test6", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2000, 7, 29);
	jum.assertEquals("add_test7", dtB, dojo.date.add(dtA, interv, 2));
	
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2001, 1, 28);
	jum.assertEquals("add_test8", dtB, dojo.date.add(dtA, interv, 4));
	
	interv = dojo.date.dateParts.MONTH;
	dtA = new Date(2000, 0, 1);
	dtB = new Date(2000, 1, 1);
	jum.assertEquals("add_test9", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2000, 0, 31);
	dtB = new Date(2000, 1, 29);
	jum.assertEquals("add_test10", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2001, 1, 28);
	jum.assertEquals("add_test11", dtB, dojo.date.add(dtA, interv, 12));
	
	interv = dojo.date.dateParts.WEEK;
	dtA = new Date(2000, 0, 1);
	dtB = new Date(2000, 0, 8);
	jum.assertEquals("add_test12", dtB, dojo.date.add(dtA, interv, 1));

	var interv = dojo.date.dateParts.DAY;
	dtA = new Date(2000, 0, 1);
	dtB = new Date(2000, 0, 2);
	jum.assertEquals("add_test13", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2001, 0, 1);
	dtB = new Date(2002, 0, 1);
	jum.assertEquals("add_test14", dtB, dojo.date.add(dtA, interv, 365));
	
	dtA = new Date(2000, 0, 1);
	dtB = new Date(2001, 0, 1);
	jum.assertEquals("add_test15", dtB, dojo.date.add(dtA, interv, 366));
	
	dtA = new Date(2000, 1, 28);
	dtB = new Date(2000, 1, 29);
	jum.assertEquals("add_test16", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2001, 1, 28);
	dtB = new Date(2001, 2, 1);
	jum.assertEquals("add_test17", dtB, dojo.date.add(dtA, interv, 1));
	
	dtA = new Date(2000, 2, 1);
	dtB = new Date(2000, 1, 29);
	jum.assertEquals("add_test18", dtB, dojo.date.add(dtA, interv, -1));
	
	dtA = new Date(2001, 2, 1);
	dtB = new Date(2001, 1, 28);
	jum.assertEquals("add_test19", dtB, dojo.date.add(dtA, interv, -1));
	
	dtA = new Date(2000, 0, 1);
	dtB = new Date(1999, 11, 31);
	jum.assertEquals("add_test20", dtB, dojo.date.add(dtA, interv, -1));
	
	interv = dojo.date.dateParts.WEEKDAY;
	// Sat, Jan 1
	dtA = new Date(2000, 0, 1);
	// Should be Mon, Jan 3
	dtB = new Date(2000, 0, 3);
	jum.assertEquals("add_test21", dtB, dojo.date.add(dtA, interv, 1));
	
	// Sun, Jan 2
	dtA = new Date(2000, 0, 2);
	// Should be Mon, Jan 3
	dtB = new Date(2000, 0, 3);
	jum.assertEquals("add_test22", dtB, dojo.date.add(dtA, interv, 1));
	
	// Sun, Jan 2
	dtA = new Date(2000, 0, 2);
	// Should be Fri, Jan 7
	dtB = new Date(2000, 0, 7);
	jum.assertEquals("add_test23", dtB, dojo.date.add(dtA, interv, 5));
	
	// Sun, Jan 2
	dtA = new Date(2000, 0, 2);
	// Should be Mon, Jan 10
	dtB = new Date(2000, 0, 10);
	jum.assertEquals("add_test24", dtB, dojo.date.add(dtA, interv, 6));
	
	// Mon, Jan 3
	dtA = new Date(2000, 0, 3);
	// Should be Mon, Jan 17
	dtB = new Date(2000, 0, 17);
	jum.assertEquals("add_test25", dtB, dojo.date.add(dtA, interv, 10));
	
	// Sat, Jan 8
	dtA = new Date(2000, 0, 8);
	// Should be Mon, Jan 3
	dtB = new Date(2000, 0, 3);
	jum.assertEquals("add_test25", dtB, dojo.date.add(dtA, interv, -5));
	
	// Sun, Jan 9
	dtA = new Date(2000, 0, 9);
	// Should be Wed, Jan 5
	dtB = new Date(2000, 0, 5);
	jum.assertEquals("add_test26", dtB, dojo.date.add(dtA, interv, -3));
	
	// Sun, Jan 23
	dtA = new Date(2000, 0, 23);
	// Should be Fri, Jan 7
	dtB = new Date(2000, 0, 7);
	jum.assertEquals("add_test27", dtB, dojo.date.add(dtA, interv, -11));
	
	interv = dojo.date.dateParts.HOUR;
	dtA = new Date(2000, 0, 1, 11);
	dtB = new Date(2000, 0, 1, 12);
	jum.assertEquals("add_test28", dtB, dojo.date.add(dtA, interv, 1));

	dtA = new Date(2001, 9, 28, 0);
	dtB = new Date(2001, 9, 28, 1);
	jum.assertEquals("add_test29", dtB, dojo.date.add(dtA, interv, 1));

	dtA = new Date(2001, 9, 28, 23);
	dtB = new Date(2001, 9, 29, 0);
	jum.assertEquals("add_test30", dtB, dojo.date.add(dtA, interv, 1));

	dtA = new Date(2001, 11, 31, 23);
	dtB = new Date(2002, 0, 1, 0);
	jum.assertEquals("add_test31", dtB, dojo.date.add(dtA, interv, 1));

	interv = dojo.date.dateParts.MINUTE;
	dtA = new Date(2000, 11, 31, 23, 59);
	dtB = new Date(2001, 0, 1, 0, 0);
	jum.assertEquals("add_test32", dtB, dojo.date.add(dtA, interv, 1));

	dtA = new Date(2000, 11, 27, 12, 02);
	dtB = new Date(2000, 11, 27, 13, 02);
	jum.assertEquals("add_test33", dtB, dojo.date.add(dtA, interv, 60));
	
	interv = dojo.date.dateParts.SECOND;
	dtA = new Date(2000, 11, 31, 23, 59, 59);
	dtB = new Date(2001, 0, 1, 0, 0, 0);
	jum.assertEquals("add_test34", dtB, dojo.date.add(dtA, interv, 1));

	dtA = new Date(2000, 11, 27, 8, 10, 59);
	dtB = new Date(2000, 11, 27, 8, 11, 59);
	jum.assertEquals("add_test35", dtB, dojo.date.add(dtA, interv, 60));
	
	// Test environment JS Date doesn't support millisec?
	//interv = dojo.date.dateParts.MILLISECOND;
	//
	//dtA = new Date(2000, 11, 31, 23, 59, 59, 999);
	//dtB = new Date(2001, 0, 1, 0, 0, 0, 0);
	//jum.assertEquals("add_test36", dtB, dojo.date.add(dtA, interv, 1));
	//
	//dtA = new Date(2000, 11, 27, 8, 10, 53, 2);
	//dtB = new Date(2000, 11, 27, 8, 10, 54, 2);
	//jum.assertEquals("add_test37", dtB, dojo.date.add(dtA, interv, 1000));
}


function test_date_diff() {
	var dtA = null; // First date to compare
	var dtB = null; // Second date to compare
	var interv = ''; // Interval to compare on (e.g., year, month)
	
	interv = dojo.date.dateParts.YEAR;
	dtA = new Date(2005, 11, 27);
	dtB = new Date(2006, 11, 27);
	jum.assertEquals("diff_test1", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 11, 31);
	dtB = new Date(2001, 0, 1);
	jum.assertEquals("diff_test2", 1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.QUARTER;
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2001, 2, 1);
	jum.assertEquals("diff_test3", 4, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 11, 1);
	dtB = new Date(2001, 0, 1);
	jum.assertEquals("diff_test4", 1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.MONTH;
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2001, 2, 1);
	jum.assertEquals("diff_test5", 13, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 11, 1);
	dtB = new Date(2001, 0, 1);
	jum.assertEquals("diff_test6", 1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.WEEK;
	dtA = new Date(2000, 1, 1);
	dtB = new Date(2000, 1, 8);
	jum.assertEquals("diff_test7", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 1, 28);
	dtB = new Date(2000, 2, 6);
	jum.assertEquals("diff_test8", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 2, 6);
	dtB = new Date(2000, 1, 28);
	jum.assertEquals("diff_test9", -1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.DAY;
	dtA = new Date(2000, 1, 29);
	dtB = new Date(2000, 2, 1);
	jum.assertEquals("diff_test10", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 11, 31);
	dtB = new Date(2001, 0, 1);
	jum.assertEquals("diff_test11", 1, dojo.date.diff(dtA, dtB, interv));
	
	// DST leap -- check for rounding err
	// This is dependent on US calendar, but
	// shouldn't break in other locales
	dtA = new Date(2005, 3, 3);
	dtB = new Date(2005, 3, 4);
	jum.assertEquals("diff_test12", 1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.WEEKDAY;
	dtA = new Date(2006, 7, 3);
	dtB = new Date(2006, 7, 11);
	jum.assertEquals("diff_test13", 6, dojo.date.diff(dtA, dtB, interv));
	
	// Positive diffs
	dtA = new Date(2006, 7, 4);
	dtB = new Date(2006, 7, 11);
	jum.assertEquals("diff_test14", 5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 5);
	dtB = new Date(2006, 7, 11);
	jum.assertEquals("diff_test15", 5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 6);
	dtB = new Date(2006, 7, 11);
	jum.assertEquals("diff_test16", 5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 7);
	dtB = new Date(2006, 7, 11);
	jum.assertEquals("diff_test17", 4, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 7);
	dtB = new Date(2006, 7, 13);
	jum.assertEquals("diff_test18", 4, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 7);
	dtB = new Date(2006, 7, 14);
	jum.assertEquals("diff_test19", 5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 7);
	dtB = new Date(2006, 7, 15);
	jum.assertEquals("diff_test20", 6, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 7);
	dtB = new Date(2006, 7, 28);
	jum.assertEquals("diff_test21", 15, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 2, 2);
	dtB = new Date(2006, 2, 28);
	jum.assertEquals("diff_test22", 18, dojo.date.diff(dtA, dtB, interv));
	
	// Negative diffs
	dtA = new Date(2006, 7, 11);
	dtB = new Date(2006, 7, 4);
	jum.assertEquals("diff_test23", -5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 11);
	dtB = new Date(2006, 7, 5);
	jum.assertEquals("diff_test24", -4, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 11);
	dtB = new Date(2006, 7, 6);
	jum.assertEquals("diff_test25", -4, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 11);
	dtB = new Date(2006, 7, 7);
	jum.assertEquals("diff_test26", -4, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 13);
	dtB = new Date(2006, 7, 7);
	jum.assertEquals("diff_test27", -5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 14);
	dtB = new Date(2006, 7, 7);
	jum.assertEquals("diff_test28", -5, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 15);
	dtB = new Date(2006, 7, 7);
	jum.assertEquals("diff_test29", -6, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 7, 28);
	dtB = new Date(2006, 7, 7);
	jum.assertEquals("diff_test30", -15, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2006, 2, 28);
	dtB = new Date(2006, 2, 2);
	jum.assertEquals("diff_test31", -18, dojo.date.diff(dtA, dtB, interv));

	// Two days on the same weekend -- no weekday diff
	dtA = new Date(2006, 7, 5);
	dtB = new Date(2006, 7, 6);
	jum.assertEquals("diff_test32", 0, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.HOUR;
	dtA = new Date(2000, 11, 31, 23);
	dtB = new Date(2001, 0, 1, 0);
	jum.assertEquals("diff_test33", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 11, 31, 12);
	dtB = new Date(2001, 0, 1, 0);
	jum.assertEquals("diff_test34", 12, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.MINUTE;
	dtA = new Date(2000, 11, 31, 23, 59);
	dtB = new Date(2001, 0, 1, 0, 0);
	jum.assertEquals("diff_test35", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 1, 28, 23, 59);
	dtB = new Date(2000, 1, 29, 0, 0);
	jum.assertEquals("diff_test36", 1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.SECOND;
	dtA = new Date(2000, 11, 31, 23, 59, 59);
	dtB = new Date(2001, 0, 1, 0, 0, 0);
	jum.assertEquals("diff_test37", 1, dojo.date.diff(dtA, dtB, interv));
	
	interv = dojo.date.dateParts.MILLISECOND;
	dtA = new Date(2000, 11, 31, 23, 59, 59, 999);
	dtB = new Date(2001, 0, 1, 0, 0, 0, 0);
	jum.assertEquals("diff_test38", 1, dojo.date.diff(dtA, dtB, interv));
	
	dtA = new Date(2000, 11, 31, 23, 59, 59, 0);
	dtB = new Date(2001, 0, 1, 0, 0, 0, 0);
	jum.assertEquals("diff_test39", 1000, dojo.date.diff(dtA, dtB, interv));
}
