/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/


dojo.require('dojo.gfx.color');
dojo.require('dojo.gfx.color.hsv');

function test_gfx_color_rgb2hsv() {
	var opts = {};
	var arrFrom = [];
	var arrTo = [];
	var arrCompare = [];
	
	// Default opts -- input and output as 0-255 range
	// ---------------
	opts = null;
	arrFrom = [198, 45, 75];
	arrCompare = [247, 197, 198];
	
	// Separate params
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_rgb2hsv1', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom, opts);
	jum.assertEquals('gfx_color_rgb2hsv2', arrCompare.join(), arrTo.join());
	
	// Default opts -- input and output as 0-255 range
	// ---------------
	opts = null;
	arrFrom = [255, 0, 0];
	arrCompare = [255, 255, 255];
	
	// Separate params
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_rgb2hsv3', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom, opts);
	jum.assertEquals('gfx_color_rgb2hsv4', arrCompare.join(), arrTo.join());
	
	// Input in 0-1.0 range
	// ---------------
	opts = { 'inputRange': 1 }
	arrFrom = [0.78, 0.18, 0.29];
	arrCompare = [247, 196, 199];
	
	// Separate params
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_rgb2hsv5', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom, opts);
	jum.assertEquals('gfx_color_rgb2hsv6', arrCompare.join(), arrTo.join());
	
	// Input in 0-100 range
	// ---------------
	opts = { 'inputRange': 100 }
	arrFrom = [78, 18, 29];
	arrCompare = [247, 196, 199];
	
	// Separate params
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_rgb2hsv7', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom, opts);
	jum.assertEquals('gfx_color_rgb2hsv8', arrCompare.join(), arrTo.join());
	
	// Output as PS/GIMP -- 360/100/100
	// ---------------
	opts = { 'outputRange': [360, 100, 100] }
	arrFrom = [198, 45, 75];
	arrCompare = [348, 77, 78];
	
	// Separate params
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_rgb2hsv9', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom, opts);
	jum.assertEquals('gfx_color_rgb2hsv10', arrCompare.join(), arrTo.join());
	
	// Output as PS/GIMP -- 360/100/100
	// ---------------
	opts = { 'outputRange': [360, 100, 100] }
	arrFrom = [255, 0, 0];
	arrCompare = [360, 100, 100];
	
	// Separate params
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_rgb2hsv11', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.rgb2hsv(arrFrom, opts);
	jum.assertEquals('gfx_color_rgb2hsv12', arrCompare.join(), arrTo.join());
}

function test_gfx_color_hsv2rgb() {
	var opts = {};
	var arrFrom = [];
	var arrTo = [];
	var arrCompare = [];
	
	// Input like PS/GIMP
	// ---------------
	opts = { 'inputRange': [360, 100, 100] };
	arrFrom = [210, 80, 100];
	arrCompare = [51, 153, 255];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb1', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb2', arrCompare.join(), arrTo.join());
	
	// Input with hue 0-360, 0-1 for sat/val
	// ---------------
	opts = { 'inputRange': [360, 1, 1] };
	arrFrom = [210, 0.8, 1];
	arrCompare = [51, 153, 255];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb3', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb4', arrCompare.join(), arrTo.join());
	
	// Output RBG as a percent
	// ---------------
	opts = { 'outputRange': 100 };
	arrFrom = [149, 204, 255];
	arrCompare = [20, 60, 100];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb5', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb6', arrCompare.join(), arrTo.join());
	
	// Default opts -- input and output as 0-255 range
	// ---------------
	opts = null;
	arrFrom = [149, 204, 255];
	arrCompare = [51, 152, 255];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb7', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb8', arrCompare.join(), arrTo.join());
	
	// Input like PS/GIMP
	// ---------------
	opts = { 'inputRange': [360, 100, 100] };
	arrFrom = [141, 100, 80];
	arrCompare = [0, 204, 71];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb9', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb10', arrCompare.join(), arrTo.join());
	
	// Input with hue 0-360, 0-1 for sat/val
	// ---------------
	opts = { 'inputRange': [360, 1, 1] };
	arrFrom = [141, 1, 0.8];
	arrCompare = [0, 204, 71];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb11', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb12', arrCompare.join(), arrTo.join());
	
	// Output RBG as a percent
	// ---------------
	opts = { 'outputRange': 100 };
	arrFrom = [100, 255, 204];
	arrCompare = [0, 80, 28];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb13', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb14', arrCompare.join(), arrTo.join());
	
	// Default opts -- input and output as 0-255 range
	// ---------------
	opts = null;
	arrFrom = [100, 255, 204];
	arrCompare = [0, 204, 72];
	
	// Separate params
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom[0], arrFrom[1], arrFrom[2], opts);
	jum.assertEquals('gfx_color_hsv2rgb15', arrCompare.join(), arrTo.join());
	
	// Array param
	arrTo = dojo.gfx.color.hsv2rgb(arrFrom, opts);
	jum.assertEquals('gfx_color_hsv2rgb16', arrCompare.join(), arrTo.join());
}

