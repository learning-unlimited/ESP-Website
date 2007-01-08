/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.string.extras");

function test_string_substituteParams(){
	var tpla = "This %{string} has %{parameters} %{toReplace}";
	var ps0 = dojo.string.substituteParams(tpla, { string: "area", parameters: "foo", toReplace: "bar"});
	jum.assertEquals("test20", "This area has foo bar", ps0);

	var thrown = false;
	try {
		// Missing a required parameter
		var ps1 = dojo.string.substituteParams(tpla, { string: "area", parameters: "foo", extra: "baz"});
	}catch(e){
		thrown = e; // exception must be thrown
	}
	jum.assertTrue("test21", thrown);

	var tplb = "Passed as arguments: %{0}, %{1}, %{2}.";
	var ps2 = dojo.string.substituteParams(tplb, "zero", "one", "two");
	jum.assertEquals("test22", "Passed as arguments: zero, one, two.", ps2);

	// Unused argument provided
	var tplb = "Passed as arguments: %{0}, %{1}, %{2}.";
	var ps3 = dojo.string.substituteParams(tplb, "zero", "one", "two", "three");
	jum.assertEquals("test23", "Passed as arguments: zero, one, two.", ps2);

	thrown = false;
	try{
		// Missing a required parameter
		var ps4 = dojo.string.substituteParams(tplb, "zero", "one");
	}catch(e){
		thrown = e; // exception must be thrown
	}
	jum.assertTrue("test24", thrown);
}

function test_string_isBlank(){
	jum.assertTrue("test40", dojo.string.isBlank('   '));
	jum.assertFalse("test50", dojo.string.isBlank('            x'));
	jum.assertFalse("test60", dojo.string.isBlank('x             '));
	jum.assertTrue("test70", dojo.string.isBlank(''));
	jum.assertTrue("test80", dojo.string.isBlank(null));
	jum.assertTrue("test90", dojo.string.isBlank(new Array()));
}

function test_string_capitalize(){
	jum.assertEquals("test100", 'This Is A Bunch Of Words', dojo.string.capitalize('this is a bunch of words'));
	jum.assertEquals("test110", 'Word', dojo.string.capitalize('word'));
	jum.assertEquals("test120", '   ', dojo.string.capitalize('   '));
	jum.assertEquals("test130", '', dojo.string.capitalize(''));
	jum.assertEquals("test140", '', dojo.string.capitalize(null));
	jum.assertEquals("test150", '', dojo.string.capitalize(new Array()));
	jum.assertEquals("test160", "This One Has  Extra   Space", dojo.string.capitalize("this one has  extra   space"));
}

function test_string_escape() {
	// TODO: vary the tests a bit more :)
	// xml | html
	jum.assertEquals("test200", '&lt;body bgcolor=&quot;#ffcc00&quot;&gt;&amp; becomes &amp;amp; y&#39;all!',
		dojo.string.escape("xml", '<body bgcolor="#ffcc00">& becomes &amp; y\'all!'));
	jum.assertEquals("test201", '&lt;body bgcolor=&quot;#ffcc00&quot;&gt;&amp; becomes &amp;amp; y&#39;all!',
		dojo.string.escape("html", '<body bgcolor="#ffcc00">& becomes &amp; y\'all!'));
	jum.assertEquals("test202", '&lt;body bgcolor=&quot;#ffcc00&quot;&gt;&amp; becomes &amp;amp; y&#39;all!',
		dojo.string.escapeXml('<body bgcolor="#ffcc00">& becomes &amp; y\'all!'));
	// sql
	jum.assertEquals("test210", "Hey y''all! How is it ''''going''''?",
		dojo.string.escape("sql", "Hey y'all! How is it ''going''?"));
	jum.assertEquals("test210", "Hey y''all! How is it ''''going''''?",
		dojo.string.escapeSql("Hey y'all! How is it ''going''?"));
	// regexp
	jum.assertEquals("test220", "wrong \\\\ divide",
		dojo.string.escape("regexp", "wrong \\ divide"));
	jum.assertEquals("test221", "wrong \\\\ divide",
		dojo.string.escape("regex", "wrong \\ divide"));
	jum.assertEquals("test222", "wrong \\\\ divide",
		dojo.string.escapeRegExp("wrong \\ divide"));
	// js
	jum.assertEquals("test230", "I have \\\"quotes\\\" of various \\'types\\'",
		dojo.string.escape("javascript", "I have \"quotes\" of various 'types'"));
	jum.assertEquals("test231", "I have \\\"quotes\\\" of various \\'types\\'",
		dojo.string.escape("js", "I have \"quotes\" of various 'types'"));
	jum.assertEquals("test232", "I have \\\"quotes\\\" of various \\'types\\'",
		dojo.string.escapeJavaScript("I have \"quotes\" of various 'types'"));
}

function test_string_summary() {
	jum.assertEquals("test300", "Every good boy do...",
		dojo.string.summary("Every good boy does fine", 17));
	jum.assertEquals("test300", "Hey Mr...",
		dojo.string.summary("Hey Mr. Jones", 6));
	jum.assertEquals("test300", "I like candy",
		dojo.string.summary("I like candy", 30));
}

function test_normalizeNewlines() {
	var t1 = "blahblahblah\r\nblahblahblah\rblahblhablhablhablh\nblahbalhablhablhab";
	var r1 = "blahblahblah\nblahblahblah\nblahblhablhablhablh\nblahbalhablhablhab";
	var r2 = "blahblahblah\rblahblahblah\rblahblhablhablhablh\rblahbalhablhablhab";
	var r3 = "blahblahblah\r\nblahblahblah\r\nblahblhablhablhablh\r\nblahbalhablhablhab";

	jum.assertEquals("test401", r1, dojo.string.normalizeNewlines(t1,'\n'));
	jum.assertEquals("test402", r2, dojo.string.normalizeNewlines(t1,'\r'));
	jum.assertEquals("test403", r3, dojo.string.normalizeNewlines(t1));
}
