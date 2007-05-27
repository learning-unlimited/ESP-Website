/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.widget.Chart");
dojo.require("dojo.widget.SortableTable");

function ChartBindingHack(div, resultSet, attributeMapping) {
	this._div = div;
	this._resultSet = resultSet;
	this._attributeMapping = attributeMapping;
	resultSet.addObserver(this);
	this.redisplayWidget();
};

ChartBindingHack.prototype.redisplayWidget = function() {
	this._div.innerHTML = this.getHtmlString();
	var parser = new dojo.xml.Parse();
	var frag = parser.parseElement(this._div, null, true);
	dojo.widget.getParser().createComponents(frag);
};

ChartBindingHack.prototype.observedObjectHasChanged = function() {
	this.redisplayWidget();
};

ChartBindingHack.prototype.getHtmlString = function() {
	var arrayOfItems = this._resultSet.toArray();
	var map = this._attributeMapping;
	var arrayOfStrings = [];
	arrayOfStrings.push('<div dojoType="chart" style="border:1px solid black;width:420px;background-color:#ededde;">');
	arrayOfStrings.push('	<table ');
	arrayOfStrings.push('			width="420" ');
	arrayOfStrings.push('			height="200" ');
	arrayOfStrings.push('			padding="24" ');
	arrayOfStrings.push('			plotType="line" ');
	arrayOfStrings.push('			axisAt="0 0" ');
	arrayOfStrings.push('			rangeX="-50 50" ');
	arrayOfStrings.push('			rangeY="-50 50" >');
	arrayOfStrings.push('		<thead>');
	arrayOfStrings.push('			<tr>');

	arrayOfStrings.push('				<th>' + map.x + '</th>');
	for (var i in map.plots) {
		var plot = map.plots[i];
		var plotType = plot["plotType"];
		var y = plot["y"];
		var size = plot["size"];
		var plotTypeString = '';
		if (plotType) {
			plotTypeString = ' plotType="' + plotType + '"';
		}
		arrayOfStrings.push('				<th' + plotTypeString + '>' + y + '</th>');
	}
	arrayOfStrings.push('			</tr>');
	arrayOfStrings.push('		</thead>');
	arrayOfStrings.push('		<tbody>');
	
	for (var i in arrayOfItems) {
		var item = arrayOfItems[i];
		var rowString = '			<tr>';
		rowString += '<td>' + item.get(map.x) + '</td>';
		for (var j in map.plots) {
			var plot = map.plots[j];
			var plotType = plot["plotType"];
			var y = plot["y"];
			var size = plot["size"];
			if (plotType == "bubble") {
				rowString += '<td size="' + item.get(size) + '">' + item.get(y) + '</td>';
			} else {
				rowString += '<td>' + item.get(y) + '</td>';
			}
		}
		rowString += '</tr>';
		arrayOfStrings.push(rowString);
	}
	arrayOfStrings.push('		</tbody>');
	arrayOfStrings.push('	</table>');
	arrayOfStrings.push('</div>');
	var returnString = arrayOfStrings.join('\n');
	return returnString;
};


// =======================================================================
function TableBindingHack(div, resultSet, attributeMapping) {
	this._div = div;
	this._resultSet = resultSet;
	this._attributeMapping = attributeMapping;
	resultSet.addObserver(this);
	this.redisplayWidget();
};

TableBindingHack.prototype.redisplayWidget = function() {
	this._div.innerHTML = this.getHtmlString();
	var parser = new dojo.xml.Parse();
	var frag = parser.parseElement(this._div, null, true);
	dojo.widget.getParser().createComponents(frag);
};

TableBindingHack.prototype.observedObjectHasChanged = function() {
	this.redisplayWidget();
};

TableBindingHack.prototype.getHtmlString = function() {
	var dataProvider = this._resultSet.getDataProvider();
	var arrayOfItems = this._resultSet.toArray();
	var arrayOfStrings = [];
	arrayOfStrings.push('<table dojoType="SortableTable" enableAlternateRows="true" cellpadding="0" cellspacing="0">');
	arrayOfStrings.push('	<thead>');
	arrayOfStrings.push('		<tr>');
	var map = this._attributeMapping;
	for (var i in map) {
		var attributeId = map[i];
		var attribute = dataProvider.getAttribute(attributeId);
		var dataTypeString = "Number"; // default is "Number" -- SortableTable also supports "String" and "Date"
		var type = attribute.get('type');
		if (type) {
			dataTypeString = type;
		}
		var nameString = attributeId;
		var name = attribute.getName();
		if (name) {
			nameString = name;
		}
		arrayOfStrings.push('			<td field="' + attributeId + '" dataType="' + dataTypeString + '">' + nameString + '</td>');
	}
	
	//		<td field="Id" dataType="Number">Id</td>');
	//		<td field="Name" dataType="String">Name</td>
	//		<td field="DateAdded" dataType="Date">Date Added</td>
	//		<td field="DateModified" dataType="Date" format="#MMM #d, #yyyy">Date Modified</td>
	//		<td>Label</td>
			
	arrayOfStrings.push('		</tr>');
	arrayOfStrings.push('	</thead>');
	arrayOfStrings.push('	<tbody>');
	for (var i in arrayOfItems) {
		var item = arrayOfItems[i];
		var rowString = '		<tr>';
		for (var j in map) {
			var attributeId = map[j];
			rowString += '<td>' + item.get(attributeId) + '</td>';
		}
		rowString += '</tr>';
		arrayOfStrings.push(rowString);
	}
	arrayOfStrings.push('	</tbody>');
	arrayOfStrings.push('</table>');
	var returnString = arrayOfStrings.join('\n');
	return returnString;
};
