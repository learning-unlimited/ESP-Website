/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.math");

function test_math_degToRad(){
	jum.assertEquals("test", Math.PI, dojo.math.degToRad(180));
}

function test_math_radToDeg(){
	jum.assertEquals("test", 180, dojo.math.radToDeg(Math.PI));
}

function test_math_factorial(){
	jum.assertEquals("test", 6, dojo.math.factorial(3));
}

function test_math_permutations(){
	jum.assertEquals("test", 24, dojo.math.permutations(4, 3));
}

function test_math_combinations(){
	jum.assertEquals("test", 4, dojo.math.combinations(4, 3));
}

function test_math_gaussianRandom () {
	// There is no way that we can assert that this function is working or not.
	// Sampling and testing whether the mean and variance would make sense, but
	// if the numbers are truely random this would tell us nothing useful other
	// than the function may or may not be working!
}

function test_math_mean () {
	jum.assertEquals("test1", 4, dojo.math.mean([2, 4, 6]));
	jum.assertEquals("test2", -4, dojo.math.mean(-3.5, -4, -4.5));
}

function test_math_round () {
	jum.assertEquals("test1", 4, dojo.math.round(4.380));
	jum.assertEquals("test2", 4, dojo.math.round(3.780));
	jum.assertEquals("test3", 3.8, dojo.math.round(3.780, 1));
	jum.assertEquals("test4", 3.78, dojo.math.round(3.781, 2));
}

function test_math_sd () {
	// see: http://en.wikipedia.org/wiki/Standard_deviation
	var data = [5, 6, 8, 9];
	jum.assertEquals("test1", 1.5811, dojo.math.round(dojo.math.sd(data), 4));
}

function test_math_variance () {
}

