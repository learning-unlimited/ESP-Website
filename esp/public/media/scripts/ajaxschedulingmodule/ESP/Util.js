// isString() courtesy of <http://www.planetpdf.com/developer/article.asp?ContentID=testing_for_object_types_in_ja>
// Return a boolean value telling whether
// the first argument is a string. 
function isString() {
    if (arguments[0] == null) {
        return false;
    }
    if (typeof arguments[0] == 'string')
        return true;
    if (typeof arguments[0] == 'object') {
        var criterion = arguments[0].constructor.toString().match(/string/i); 
        return (criterion != null);
    }
    return false;
}


/*
 * general use functions
 */
ESP.Utilities = function(){
    var Utilities = {};
    
    Utilities.EventManager = function(){
        var evm = {};
        evm._jq_obj = $j(evm);
        evm.bind = function(type, data, fn) {
            evm._jq_obj.bind(type, data, fn);
        };
        evm.fire = function(type, data) {
            if (!$j.isArray(data)) var data = [data];
            evm._jq_obj.triggerHandler(type, data);
        };
        evm.unbind = function(type, fn) {
            evm._jq_obj.unbind(type, fn);
        };
        return evm;
    };
    
    Utilities.evm = Utilities.EventManager();

    // Takes a dictionary of key/value pairs, and returns a popup <a> DOM-object that displays them
    // JS dictionaries are apparently supposed to be ordered.  We'll see if that's actually true...
    Utilities.genPopup = function(id, label, elts, onhover, asString) {
	console.log("genPopup");
	console.log(elts);
        var root = $j("<a></a>");
        root.attr('class', 'tooltip tooltip-id-' + id);
        root.append(label);
	root.hover(function() {
	    if (onhover) {
		onhover($j(this));
	    }
	    $j(this).toggleClass('tooltip_hover');
	    $j(this).children('.tooltip_popup').toggle();
	});
    
        var span = $j("<span></span>");
	span.attr('class', 'tooltip_popup');
	span.hide();
        root.append(span);

        for (key in elts) {
            var val = elts[key];
            if (val == null) {
                break;
            }
            var boldElt = $j("<b></b>");
            boldElt.append(key);
            span.append(boldElt);

            if (isString(val)) {
                span.append(' ' + val);
                span.append($j("<br/>"));
            } else {  // Assume we have a list; add it as a <ul>
                var ul = $j("<ul></ul>");
                var any_good_vals = false;
                for (var item = 0; item < val.length; item++) {
                    if (val[item] == null) {
                        continue;
                    }
                    any_good_vals = true;
                    var li = $j("<li></li>");
                    li.append(val[item]);
                    ul.append(li);
                }
                if (any_good_vals) {
                  span.append(ul);
                } else {
                  span.append(" (none) <br/>");
                }
                //span.appendChild( document.createElement('br') );
            }
        }

        if (asString) {
            var tmpNode = $j('<tmp></tmp>');
            tmpNode.append(root);
            return tmpNode.html();
        } else {
            return root;
        }
    }


    // Takes a dictionary of key/value pairs as well as the root node of a pre-existing popup
    // and fills it in with the given values. Use this to create a popup and then fill it in
    // with dynamically loaded data
    Utilities.fillPopup = function(id, elts, asString) {
	console.log("fillPopup");
	console.log(elts);
	root = $j(".tooltip-id-" + id);

	span = root.children("span.tooltip_popup");
	if (span.length <= 0) {
	    return 0;
	}

        for (key in elts) {
            var val = elts[key];
            if (val == null) {
                break;
            }
            var boldElt = $j("<b></b>");
            boldElt.append(key);
            span.append(boldElt);

            if (isString(val)) {
                span.append(' ' + val);
                span.append('<br/>');
            } else {  // Assume we have a list; add it as a <ul>
                var ul = $j('<ul></ul>');
                var any_good_vals = false;
                for (var item = 0; item < val.length; item++) {
                    if (val[item] == null) {
                        continue;
                    }
                    any_good_vals = true;
                    var li = $j('<li></li>');
                    li.append(val[item]);
                    ul.append(li);
                }
                if (any_good_vals) {
                  span.append(ul);
                } else {
                  span.append(" (none) <br\>");
                }
                //span.appendChild( document.createElement('br') );
            }
        }

        if (asString) {
	    var tmpNode =$j("<tmp></tmp>");
            tmpNode.append(root);
            return tmpNode.html();
        } else {
            return root;
        }
    };

    // Clear the contents of a tooltip popup specified by the id
    Utilities.clearPopup = function(id) {
	root = $j(".tooltip-id-"+id);
	root.children(".tooltip-popup").html('');
    };

    return Utilities;
}();

/*
 * JQuery extensions
 */
$j.extend({
    check : function(variable) {
        return typeof variable != 'undefined' && variable;
    },
    getDefault : function(dict, key, def) {
        return ((typeof dict[key] != 'undefined') && dict[key]) || (dict[key] = def);
    }
});


/*
 * language extensions
 */
if (!Array.prototype.contains) {
    Array.prototype.contains = function(value){
        return $j.inArray(value, this) != -1;
    };
}
function cmp(one,two) {
    return one === two ? 0 : ( one > two ? 1 : -1 );
}
