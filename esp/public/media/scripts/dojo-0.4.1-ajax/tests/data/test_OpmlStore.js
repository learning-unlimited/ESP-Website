/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.data.OpmlStore");
dojo.require("dojo.lang.type");
dojo.require("dojo.io.*");
dojo.require("dojo.widget.*");
dojo.require("dojo.widget.TreeV3");
dojo.require("dojo.widget.TreeNodeV3");
dojo.require("dojo.widget.TreeBasicControllerV3");
	
function run_all_tests() {
	var store = new dojo.data.OpmlStore({url:"geography.opml"});
	var result = store.find();
	showResultViaTreeV3(result);
	showResultViaDojoDebug(result);
}

function showResultViaTreeV3(result) {
	// This doesn't quite work yet -- almost
	var controller = dojo.widget.createWidget("TreeBasicControllerV3");		
	var tree = dojo.widget.createWidget("TreeV3", {listeners:[controller.widgetId]});
	var treeDiv = dojo.byId("treeDiv");
	treeDiv.appendChild(tree.domNode);
	
	var rootTreeNode = dojo.widget.createWidget("TreeNodeV3", {title: result.store._opmlFileUrl, tree: tree.widgetId});
	tree.addChild(rootTreeNode);

	for (var i in result.items) {
		showItemAsTreeNode(result.store, result.items[i], tree, rootTreeNode);
	}
	controller.expandToLevel(tree, 1);
	// controller.expandAll(tree);
}

function showItemAsTreeNode(store, item, tree, parentTreeNode) {
	var itemName = store.get(item, 'text');
	var attributes = store.getAttributes(item);
	var description = '';
	for (var i in attributes) {
		var attribute = attributes[i];
		if (attribute != 'text' && attribute != 'children') {
			if (description) { 
				description += ', ';
			}
			description += attribute + ': "' + store.get(item, attribute) + '"';
		}
	}
	var treeNodeTitle = itemName;
	if (description) {
		treeNodeTitle += ' <font color="bbbbbb">{' + description + '}</font>'; 
	}
	var treeNode = dojo.widget.createWidget("TreeNodeV3", {title: treeNodeTitle, tree: tree.widgetId});
	parentTreeNode.addChild(treeNode);
	var children = store.getValues(item, 'children');
	for (var i in children) {
		var childItem = children[i];
		showItemAsTreeNode(store, childItem, tree, treeNode);
	}
}

function showResultViaDojoDebug(result) {
	dojo.debug(result.items.length + " items returned by store.find()");
	for (var i in result.items) {
		showItemViaDojoDebug(result.store, result.items[i]);
	}
}

function showItemViaDojoDebug(store, item, indentLevel) {
	indentLevel = indentLevel || 1;
	var indentString = "....";
	var totalIndentString = "";
	for (var i = 0; i < indentLevel; ++i) {
		totalIndentString += indentString;
	}
	if (store.hasAttribute(item, 'text')) {
		var attributes = store.getAttributes(item);
		var children = store.getValues(item, 'children');
		dojo.debug(totalIndentString + 'Item: ' + store.get(item, 'text') + 
			' (' + children.length + ' children)' +
			' (' + attributes.length + ' attributes)');
		for (i = 0; i < attributes.length; ++i) {
			var attributeName = attributes[i];
			var attributeValues = store.getValues(item, attributeName);
			if (attributeValues.length == 1 && !store.isItem(attributeValues[0])) {
				dojo.debug(totalIndentString + indentString + attributeName + ': "' + attributeValues[0] + '"');
			} else {
				dojo.debug(totalIndentString + indentString + attributeName + ': ');
				var nextIndentLevel = indentLevel + 1;
				for (var j = 0; j < attributeValues.length; ++j) {
					var child = attributeValues[j];
					showItemViaDojoDebug(store, child, nextIndentLevel)
				}
			}
		}
	}
	/*
	if (item.tagName == 'outline' && item.hasAttribute('text')) {
		dojo.debug(totalIndentString + 'Item: ' + item.getAttribute('text') +  ' (' + item.childNodes.length + ' children)');
		var attributes = item.attributes;
		for (var j = 0; j < attributes.length; ++j) {
			var attribute = attributes.item(j);
			var name = attribute.name;
			var nodeName = attribute.nodeName;
			var nodeValue = attribute.nodeValue;
			dojo.debug(totalIndentString + indentString + '{' + name + ' ' + nodeName + ': "' + nodeValue + '"}');
		}
		var children = item.childNodes;
		++indentLevel;
		for (var i = 0; i < children.length; ++i) {
			var node = children[i];
			showNode(node, indentLevel);
		}
	}
	*/
}








