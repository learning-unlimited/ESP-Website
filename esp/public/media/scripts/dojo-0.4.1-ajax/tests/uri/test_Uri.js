/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.uri.Uri");

function test_uri_testBases(){
	var base = 'http://a/b/c/d;p?q';

	jum.assertEquals("test1", (new dojo.uri.Uri(base, 'g:h')).toString(), 'g:h');
	jum.assertEquals("test2", (new dojo.uri.Uri(base, 'g')).toString(), 'http://a/b/c/g');
	jum.assertEquals("test3", (new dojo.uri.Uri(base, './g')).toString(), 'http://a/b/c/g');
	jum.assertEquals("test4", (new dojo.uri.Uri(base, 'g/')).toString(), 'http://a/b/c/g/');
	jum.assertEquals("test5", (new dojo.uri.Uri(base, '/g')).toString(), 'http://a/g');
	jum.assertEquals("test6", (new dojo.uri.Uri(base, '//g')).toString(), 'http://g');
	jum.assertEquals("test7", (new dojo.uri.Uri(base, '?y')).toString(), 'http://a/b/c/?y');
	jum.assertEquals("test8", (new dojo.uri.Uri(base, 'g?y')).toString(), 'http://a/b/c/g?y');
	jum.assertEquals("test9", (new dojo.uri.Uri(base, '#s')).toString(), 'http://a/b/c/d;p?q#s');
	jum.assertEquals("test10", (new dojo.uri.Uri(base, 'g#s')).toString(), 'http://a/b/c/g#s');
	jum.assertEquals("test11", (new dojo.uri.Uri(base, 'g?y#s')).toString(), 'http://a/b/c/g?y#s');
	jum.assertEquals("test12", (new dojo.uri.Uri(base, ';x')).toString(), 'http://a/b/c/;x');
	jum.assertEquals("test13", (new dojo.uri.Uri(base, 'g;x')).toString(), 'http://a/b/c/g;x');
	jum.assertEquals("test14", (new dojo.uri.Uri(base, 'g;x?y#s')).toString(), 'http://a/b/c/g;x?y#s');
	jum.assertEquals("test15", (new dojo.uri.Uri(base, '.')).toString(), 'http://a/b/c/');
	jum.assertEquals("test16", (new dojo.uri.Uri(base, './')).toString(), 'http://a/b/c/');
	jum.assertEquals("test17", (new dojo.uri.Uri(base, '..')).toString(), 'http://a/b/');
	jum.assertEquals("test18", (new dojo.uri.Uri(base, '../')).toString(), 'http://a/b/');
	jum.assertEquals("test19", (new dojo.uri.Uri(base, '../g')).toString(), 'http://a/b/g');
	jum.assertEquals("test20", (new dojo.uri.Uri(base, '../..')).toString(), 'http://a/');
	jum.assertEquals("test21", (new dojo.uri.Uri(base, '../../')).toString(), 'http://a/');
	jum.assertEquals("test22", (new dojo.uri.Uri(base, '../../g')).toString(), 'http://a/g');

	jum.assertEquals("test23", (new dojo.uri.Uri(base, '')).toString(), base);

	jum.assertEquals("test24", (new dojo.uri.Uri(base, '../../../g')).toString(), 'http://a/../g');
	jum.assertEquals("test25", (new dojo.uri.Uri(base, '../../../../g')).toString(), 'http://a/../../g');

	jum.assertEquals("test26", (new dojo.uri.Uri(base, '/./g')).toString(), 'http://a/./g');
	jum.assertEquals("test27", (new dojo.uri.Uri(base, '/../g')).toString(), 'http://a/../g');
	jum.assertEquals("test28", (new dojo.uri.Uri(base, 'g.')).toString(), 'http://a/b/c/g.');
	jum.assertEquals("test29", (new dojo.uri.Uri(base, '.g')).toString(), 'http://a/b/c/.g');
	jum.assertEquals("test30", (new dojo.uri.Uri(base, 'g..')).toString(), 'http://a/b/c/g..');
	jum.assertEquals("test31", (new dojo.uri.Uri(base, '..g')).toString(), 'http://a/b/c/..g');

	jum.assertEquals("test32", (new dojo.uri.Uri(base, './../g')).toString(), 'http://a/b/g');
	jum.assertEquals("test33", (new dojo.uri.Uri(base, './g/.')).toString(), 'http://a/b/c/g/');
	jum.assertEquals("test34", (new dojo.uri.Uri(base, 'g/./h')).toString(), 'http://a/b/c/g/h');
	jum.assertEquals("test35", (new dojo.uri.Uri(base, 'g/../h')).toString(), 'http://a/b/c/h');
	jum.assertEquals("test36", (new dojo.uri.Uri(base, 'g;x=1/./y')).toString(), 'http://a/b/c/g;x=1/y');
	jum.assertEquals("test37", (new dojo.uri.Uri(base, 'g;x=1/../y')).toString(), 'http://a/b/c/y');

	jum.assertEquals("test38", (new dojo.uri.Uri(base, 'g?y/./x')).toString(), 'http://a/b/c/g?y/./x');
	jum.assertEquals("test39", (new dojo.uri.Uri(base, 'g?y/../x')).toString(), 'http://a/b/c/g?y/../x');
	jum.assertEquals("test40", (new dojo.uri.Uri(base, 'g#s/./x')).toString(), 'http://a/b/c/g#s/./x');
	jum.assertEquals("test41", (new dojo.uri.Uri(base, 'g#s/../x')).toString(), 'http://a/b/c/g#s/../x');
}
