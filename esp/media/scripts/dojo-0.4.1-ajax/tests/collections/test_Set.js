/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.Set");

var a = ["apple","bear","candy","donut","epiphite","frank"];
var b = ["bear","epiphite","google","happy","joy"];
function test_Set_union(){ 
	var union = dojo.collections.Set.union(a,b);
	jum.assertEquals(
		"dojo.collections.Set.union", 
		"apple,bear,candy,donut,epiphite,frank,google,happy,joy", 
		union.toArray().join(",")
	);
}
function test_Set_intersection(){ 
	var intersection=dojo.collections.Set.intersection(a,b);
	jum.assertEquals(
		"dojo.collections.Set.intersection", 
		"bear,epiphite", 
		intersection.toArray().join(",")
	);
	jum.assertEquals(
		"dojo.collections.Set.intersection", 
		"bear",
		dojo.collections.Set.intersection(["bear","apple"],["bear"])
	);
}
function test_Set_difference(){ 
	var diff = dojo.collections.Set.difference(a,b);
	jum.assertEquals(
		"dojo.collections.Set.difference", 
		"apple,candy,donut,frank", 
		diff.toArray().join(",")
	);
	var diff = dojo.collections.Set.difference(b,a);
	jum.assertEquals(
		"dojo.collections.Set.difference", 
		"google,happy,joy", 
		diff.toArray().join(",")
	);
}
function test_Set_isSubSet(){ 
	jum.assertEquals(
		"dojo.collections.Set.isSubSet 1", 
		false, 
		dojo.collections.Set.isSubSet(a,["bear","candy"])
	);
	jum.assertEquals(
		"dojo.collections.Set.isSubSet 2", 
		true, 
		dojo.collections.Set.isSubSet(["bear","candy"],a)
	);

}
function test_Set_isSuperSet(){ 
	jum.assertEquals(
		"dojo.collections.Set.isSuperSet", 
		true, 
		dojo.collections.Set.isSuperSet(a,["bear","candy"])
	);
	jum.assertEquals(
		"dojo.collections.Set.isSuperSet", 
		false, 
		dojo.collections.Set.isSuperSet(["bear","candy"],a)
	);
}
