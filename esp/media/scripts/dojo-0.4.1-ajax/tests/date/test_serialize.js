/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.date.serialize");

function test_date_rfc3339() {
	var rfc  = "2005-06-29T08:05:00-07:00";
	var date = dojo.date.fromRfc3339(rfc);
	jum.assertEquals("rfc3339_test1",2005,date.getFullYear());
	jum.assertEquals("rfc3339_test2",5,date.getMonth());
	jum.assertEquals("rfc3339_test3",29,date.getDate());
	jum.assertEquals("rfc3339_test4",15,date.getUTCHours());
	jum.assertEquals("rfc3339_test5",5,date.getMinutes());
	jum.assertEquals("rfc3339_test6",0,date.getSeconds());

	rfc  = "2004-02-29Tany";
	date = dojo.date.fromRfc3339(rfc);
	jum.assertEquals("rfc3339_test7",2004,date.getFullYear());
	jum.assertEquals("rfc3339_test8",1,date.getMonth());
	jum.assertEquals("rfc3339_test9",29,date.getDate());

	date = new Date(2005,5,29,8,5,0);
	rfc = dojo.date.toRfc3339(date);
	//truncate for comparison
	jum.assertEquals("rfc3339_test10","2005-06",rfc.substring(0,7));
}

/* ISO 8601 Functions
 *********************/

function test_date_fromIso8601() {
	var iso  = "20060210T000000Z";
	var date = dojo.date.fromIso8601(iso);
	jum.assertEquals("fromIso8601_test1",2006,date.getFullYear());
	jum.assertEquals("fromIso8601_test2",1,date.getMonth());
	jum.assertEquals("fromIso8601_test3",10,date.getUTCDate());
}

function test_date_fromIso8601Date () {
	
	//YYYY-MM-DD
	var date = dojo.date.fromIso8601Date("2005-02-22");
	jum.assertEquals("fromIso8601Date_test7", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test8", 1, date.getMonth());
	jum.assertEquals("fromIso8601Date_test9", 22, date.getDate());
	
	//YYYYMMDD
	var date = dojo.date.fromIso8601Date("20050222");
	jum.assertEquals("fromIso8601Date_test10", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test11", 1, date.getMonth());
	jum.assertEquals("fromIso8601Date_test12", 22, date.getDate());
	
	//YYYY-MM
	var date = dojo.date.fromIso8601Date("2005-08");
	jum.assertEquals("fromIso8601Date_test13", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test14", 7, date.getMonth());
	
	//YYYYMM
	var date = dojo.date.fromIso8601Date("200502");
	jum.assertEquals("fromIso8601Date_test15", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test16", 1, date.getMonth());
	
	//YYYY
	var date = dojo.date.fromIso8601Date("2005");
	jum.assertEquals("fromIso8601Date_test17", 2005, date.getFullYear());
	
	//1997-W01 or 1997W01
	var date = dojo.date.fromIso8601Date("2005-W22");
	jum.assertEquals("fromIso8601Date_test18", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test19", 5, date.getMonth());
	jum.assertEquals("fromIso8601Date_test20", 6, date.getDate());

	var date = dojo.date.fromIso8601Date("2005W22");
	jum.assertEquals("fromIso8601Date_test21", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test22", 5, date.getMonth());
	jum.assertEquals("fromIso8601Date_test23", 6, date.getDate());
	
	//1997-W01-2 or 1997W012
	var date = dojo.date.fromIso8601Date("2005-W22-4");
	jum.assertEquals("fromIso8601Date_test24", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test25", 5, date.getMonth());
	jum.assertEquals("fromIso8601Date_test26", 9, date.getDate());

	var date = dojo.date.fromIso8601Date("2005W224");
	jum.assertEquals("fromIso8601Date_test27", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test28", 5, date.getMonth());
	jum.assertEquals("fromIso8601Date_test29", 9, date.getDate());

		
	//1995-035 or 1995035
	var date = dojo.date.fromIso8601Date("2005-146");
	jum.assertEquals("fromIso8601Date_test30", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test31", 4, date.getMonth());
	jum.assertEquals("fromIso8601Date_test32", 26, date.getDate());
	
	var date = dojo.date.fromIso8601Date("2005146");
	jum.assertEquals("fromIso8601Date_test33", 2005, date.getFullYear());
	jum.assertEquals("fromIso8601Date_test34", 4, date.getMonth());
	jum.assertEquals("fromIso8601Date_test35", 26, date.getDate());
	
}

function test_date_fromIso8601Time () {
	
	//23:59:59
	var date = dojo.date.fromIso8601Time("18:46:39");
	jum.assertEquals("fromIso8601Time_test36", 18, date.getHours());
	jum.assertEquals("fromIso8601Time_test37", 46, date.getMinutes());
	jum.assertEquals("fromIso8601Time_test38", 39, date.getSeconds());
	
	//235959
	var date = dojo.date.fromIso8601Time("184639");
	jum.assertEquals("fromIso8601Time_test39", 18, date.getHours());
	jum.assertEquals("fromIso8601Time_test40", 46, date.getMinutes());
	jum.assertEquals("fromIso8601Time_test41", 39, date.getSeconds());
	
	//23:59, 2359, or 23
	var date = dojo.date.fromIso8601Time("18:46");
	jum.assertEquals("fromIso8601Time_test42", 18, date.getHours());
	jum.assertEquals("fromIso8601Time_test43", 46, date.getMinutes());

	var date = dojo.date.fromIso8601Time("1846");
	jum.assertEquals("fromIso8601Time_test44", 18, date.getHours());
	jum.assertEquals("fromIso8601Time_test45", 46, date.getMinutes());

	var date = dojo.date.fromIso8601Time("18");
	jum.assertEquals("fromIso8601Time_test46", 18, date.getHours());

	//23:59:59.9942 or 235959.9942
	var date = dojo.date.fromIso8601Time("18:46:39.9942");
	jum.assertEquals("fromIso8601Time_test47", 18, date.getHours());
	jum.assertEquals("fromIso8601Time_test48", 46, date.getMinutes());
	jum.assertEquals("fromIso8601Time_test49", 39, date.getSeconds());
	jum.assertEquals("fromIso8601Time_test50", 994, date.getMilliseconds());

	var date = dojo.date.fromIso8601Time("184639.9942");
	jum.assertEquals("fromIso8601Time_test51", 18, date.getHours());
	jum.assertEquals("fromIso8601Time_test52", 46, date.getMinutes());
	jum.assertEquals("fromIso8601Time_test53", 39, date.getSeconds());
	jum.assertEquals("fromIso8601Time_test54", 994, date.getMilliseconds());
	
	//1995-02-04 24:00 = 1995-02-05 00:00

	//timezone tests
	var offset = new Date().getTimezoneOffset()/60;
	var date = dojo.date.fromIso8601Time("18:46:39+07:00");
	jum.assertEquals("fromIso8601Time_test61", 11, date.getUTCHours());

	var date = dojo.date.fromIso8601Time("18:46:39+00:00");
	jum.assertEquals("fromIso8601Time_test62", 18, date.getUTCHours());

	var date = dojo.date.fromIso8601Time("16:46:39-07:00");
	jum.assertEquals("fromIso8601Time_test63", 23, date.getUTCHours());
	
	//+hh:mm, +hhmm, or +hh
	
	//-hh:mm, -hhmm, or -hh
	
}
