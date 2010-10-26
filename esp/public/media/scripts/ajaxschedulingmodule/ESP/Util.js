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
    Utilities.genPopup = function(label, elts, asString) {
        var root = document.createElement('a');
        root.setAttribute('class', 'tooltip');
        root.appendChild( document.createTextNode(label) );
    
        var span = document.createElement('span');
        root.appendChild(span);

        for (key in elts) {
  	    var val = elts[key];
	    if (val == null) {
	      break;
	    }
	    var boldElt = document.createElement('b');
	    boldElt.appendChild( document.createTextNode(key) );
	    span.appendChild(boldElt);

	    if (isString(val)) {
	        span.appendChild( document.createTextNode(' ') );
	        span.appendChild( document.createTextNode(val) );
	        span.appendChild( document.createElement('br') );
	    } else {  // Assume we have a list; add it as a <ul>
	        var ul = document.createElement('ul');
		var any_good_vals = false;
	        for (var item = 0; item < val.length; item++) {
		    if (val[item] == null) {
		      continue;
		    }
		    any_good_vals = true;
	            var li = document.createElement('li');
	            li.appendChild( document.createTextNode(val[item]) );
	            ul.appendChild(li);
	        }
		if (any_good_vals) {
		  span.appendChild(ul);
		} else {
		  span.appendChild( document.createTextNode("(none)") );
		}
		//span.appendChild( document.createElement('br') );
	    }
        }

	if (asString) {
	  var tmpNode = document.createElement('tmp');
	  tmpNode.appendChild(root);
	  return tmpNode.innerHTML;
	} else {
	  return root;
	}
    }
    
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
