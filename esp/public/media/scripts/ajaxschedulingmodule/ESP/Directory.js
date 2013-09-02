    fixed_width = function(width){
	return 'min-width:'+width.toString() + 'px;max-width:'+ width.toString()+'px;';
    };

ESP.declare('ESP.Scheduling.Widgets.Directory', Class.create({
    initialize : function(sections){
            var directory = this;
        
            this.entries = [];
            this.active_entries = [];
            this.active_sort = null;
            this.active_filter = null;
        
            // set up display
            this.table = $j("<table/>").addClass('directory');
            this.el = $j("<div id='directory-table-wrapper'/>").addClass('directory-table-wrapper');
            this.el.append(this.table);
        
            // create header
            var thead = $j('<thead/>');
            this.table.append(thead);
            this.tbody = $j('<tbody/>');
            this.table.append(this.tbody);
        
            var header = this.header = $j('<tr/>').addClass('header');
            thead.append(header);
            $j.each(this.properties, function(key, prop){
                var td = $j('<td style="'+(prop.css()||'')+'"><span>' + (prop.label || key) + '</span></td>');
                prop.header = td;
                if (prop.sort) {
                    td.addClass('sortable');
                    // enable onclick sorting
                    td.bind('click', function(e){
                        prop.reverse = (directory.active_sort != prop) ? prop.reverse : !prop.reverse;
                        directory.sort(prop);
                    });
                }
                header.append(td);
            });
        
            // add sections
            this.addEntry(sections, false);
        
            // refresh the representation
            this.filter();
	    $j('.directory-table-wrapper').css("max-width", window.innerWidth - 50);
	    $j('.directory-table-wrapper').css("min-width", 50);
        },
        
        // table columns
        properties: {
        'ID': {
            get: function(x){ return x.block_contents.clone(true); },
            //css: 'text-align:center; text-decoration:underline; font-weight:bold;',
            sort: function(x,y){
                // use code instead of emailcode; that's how Scheduling.process_data names it
                var diff = x.section.class_id - y.section.class_id;
                return diff == 0 ? cmp(x.section.code, y.section.code) : diff;
            },
	    //css: 'width:100px;'
	    /* Code to style unapproved classes differently */
            css: function(x){
		var default_css = fixed_width(70);
		var unapproved_css = "color:#ff0000; font-style:italic;";
		// if we're just calling it for the general properties of the ID td
		// or if it's approved, return the default css
		if (!x || x.status == 10) {
		    return default_css;
		}
		// if the class is not approved, apply the unapproved styling to it
		else {
		    return default_css + unapproved_css;
		}
	    }
        },
        'Title': {
            get: function(x){ return x.text; },
            sort: function(x,y){
                return cmp(x.section.text, y.section.text);
            },
	    // css: 'width:400px;'
	    /* Code to style unapproved classes differently */
            css: function(x){ 
		var default_css = 'width:400px;';
		var unapproved_css = "color:#ff0000; font-style:italic;";
		// if we're just calling it for the general properties of the ID td
		// or if it's approved, return the default css
		if (!x || x.status == 10) {
		    return default_css;
		}
		// if the class is not approved, apply the unapproved styling to it
		else {
		    return default_css + unapproved_css;
		}
	    }
        },
        'Teacher': {
            get: function(x) {
		if (x.teachers) {
		    var ret_node = $j("");
		    $j.each(x.teachers.map(
			    function(x){
				return x.block_contents.clone(true)
			    }), 
			    function(index, value){
				ret_node = ret_node.add(value);
				ret_node = ret_node.add($j("<br>"))
			    });
		    return ret_node;
		}
		else {
		    return "Loading...";
		}
	    },
            sort: function(x,y){
                return cmp(""+x.section.teachers.map(function(z){return z.text;}), ""+y.section.teachers.map(function(z){return z.text;}));
            },
	    // css: 'width:200px;'
	    /* Code to style unapproved classes differently */
            css: function(x){
		var default_css = fixed_width(150);
		var unapproved_css = "color:#ff0000; font-style:italic;";
		// if we're just calling it for the general properties of the ID td
		// or if it's approved, return the default css
		if (!x || x.status == 10) {
		    return default_css;
		}
		// if the class is not approved, apply the unapproved styling to it
		else {
		    return default_css + unapproved_css;
		}
	    }
        },
        'Length': {
            get: function(x) { return x.length_hr; },
            sort: function(x,y) {
                return x.section.length - y.section.length;
            },
	    // css: 'width:50px;'
	    /* Code to style unapproved classes differently */
            css: function(x){
		//TODO:  factor out the messy thing with min-width and max-width
		var default_css = fixed_width(50);
		var unapproved_css = "color:#ff0000; font-style:italic;";
		// if we're just calling it for the general properties of the ID td
		// or if it's approved, return the default css
		if (!x || x.status == 10) {
		    return default_css;
		}
		// if the class is not approved, apply the unapproved styling to it
		else {
		    return default_css + unapproved_css;
		}
	    }
        }
        },
        
        // filter active rows
        filter: function(filter){
	    console.log("filtering")
            var filter = filter || this.activeFilter || function(){ return true; };
            this.activeFilter = filter;
            var active_rows = [];
            $j.each(this.entries, function(i,entry){
                if (entry.section.blocks.length == 0 && filter(entry.section))
                    active_rows.push(entry);
            });
            this.active_rows = active_rows;
            this.sort();
        },

        // filter for determining active section or not
        activeFilter: function(section) {
	    var lunch_symbol = "L";
	    return section.category != lunch_symbol;
	},
        
        // sort active rows
        sort: function(prop){
            var prop = prop || this.active_sort;
            this.header.children().removeClass('sort-by asc desc');
            if (prop) {
                prop.header.addClass('sort-by').addClass(prop.reverse ? 'asc' : 'desc');
                this.active_sort = prop;
                this.active_rows.sort(prop.sort.bind(this));
                if (prop.reverse) this.active_rows.reverse();
            }
            this.update();
        },
        
        // add an entry
        addEntry: function(entry, update){
            var update = typeof update == 'undefined' ? true : update;
            if (Object.isArray(entry)) {
		// we need basic class info
		if (!entry.class_info) {
		    // TODO: fill this in
		}

                $j.each(entry, function(i,x){
                    this.entries.push(new ESP.Scheduling.Widgets.Directory.Entry(this, x));
                }.bind(this));
            } else {
                this.entries.push(new ESP.Scheduling.Widgets.Directory.Entry(this, entry));
            }
            if (update) this.filter();
        },
        
        // update directory entries
        update: function(){
            this.tbody.hide();
            this.tbody[0].innerHTML = "";//.children().remove();  // The 'right' way here is vastly slower, sadly.  -- aseering 10/23/2010
            $j.each(this.active_rows, function (i,x){ this.tbody.append(x.update().el); x.draggable(); }.bind(this));
            this.tbody.show();
        }
    }));

ESP.declare('ESP.Scheduling.Widgets.Directory.Entry', Class.create({
        initialize: function(directory, section){
            this.directory = directory;
            this.section = section;
            this.el = $j('<tr/>').addClass('class-entry').data("controller",this);
            //this.el.addClass('CLS_category_' + section.category);
	    //this.el.addClass('directory-category');
            this.el.addClass('CLS_id_' + section.id);
            this.el.addClass('CLS_length_' + section.length_hr + '_hrs');
            this.el.addClass('CLS_status_' + section.status);
            this.el.addClass('CLS_grade_min_' + section.grade_min);
            this.el.addClass('CLS_grade_max_' + section.grade_max);
	    /*
            for (var i = 0; i < section.resource_requests.length; i++) {
                if (section.resource_requests[i][0]) {
                    this.el.addClass('CLS_rsrc_req_' + section.resource_requests[i][0].text.replace(/[^a-zA-Z]+/g, '-'));
                }
            }
	    */

            this.tds = {};
            $j.each(this.directory.properties,function(index, prop){
		console.log(prop.css(section));
                var td = $j('<td style="' + (prop.css(section)||'') + '"></td>');
		td.append(prop.get(section));
                this.tds[index] = td;
                this.el.append(td);
            }.bind(this));
        },
        draggable: function(){
            ESP.Scheduling.DragDrop.make_draggable(this.el, function(){ return this.section; }.bind(this));
        },
        update: function(){
            $j.each(this.directory.properties,function(index, prop){
                this.tds[index].html(prop.get(this.section));
            }.bind(this));
            return this;
        }
    }));

ESP.declare('ESP.Scheduling.Widgets.SearchBox', Class.create({
    initialize: function(directory) {
        this.directory = directory;        
        this.el = $j('<div id="searchbox"/>').addClass('searchbox');

	//add filters to filter box
	this.filters = []
	table = $j('<table/>')
	//title and id
	var filter_names  = ["Title" , "ID"   ]
	var filter_fields = ["text"  , "code" ]
	for (var i = 0; i < filter_fields.length; i++){
	    tr = this.add_input(filter_names[i], table)
	    this.filters.push(this.get_filter(filter_fields[i], input, "text"))
	}      
	
	//teachers
	input = this.add_input("Teacher", table, "text")
	this.filters.push(this.get_teacher_filter(input))
	//length and class size
	this.add_two_inputs("Min length", "Max length", table, "length_hr")
	this.add_two_inputs("Min size", "Max size", table, "class_size_max")
	//status
	input = this.add_input("Show unapproved classes", table, "checkbox")
	this.filters.push(this.get_status_filter(input))
	input.bind('change', this.do_search.bind(this))

	this.el.append(table)
	this.directory.filter(this.all_filters.bind(this))
    },

    add_input: function(label, table, type, f){
	tr = $j('<tr>')
	input = $j('<input type="' + type + '" id="filter_'+label.replace(" ", "-")+'"/>');
	input.bind('keypress', this.do_search.bind(this));
	td = $j('<td/>').append(input)
	tr.append($j('<td valign="center" style="width: 70px">'+ label +'</td>')).append(td);
	table.append(tr)
	return input
    },

    //make more specific to min/max?
    add_two_inputs: function(label1, label2, table, attr){
	tr = $j('<tr>')
	input1 = $j('<input type="text" id="filter_'+label1.replace(" ", "-")+'"/>');
	input2 = $j('<input type="text" id="filter_'+label2.replace(" ", "-")+'"/>');
	input1.bind('keypress', this.do_search.bind(this));
	input2.bind('keypress', this.do_search.bind(this));
	td1 = $j('<td/>').append(input1)
	td2 = $j('<td/>').append(input2)
	l1 = $j('<td valign="center" style="width: 10%">'+ label1 +'</td>')
	l2 = $j('<td valign="center" style="width: 10%">'+ label2 +'</td>')
	tr.append(l1, td1, l2, td2)
	table.append(tr)
	this.filters.push(this.get_min_max_filter(input1, input2, attr))
	return tr
    },

    all_filters: function(x){
	for (var i=0; i < this.filters.length; i ++){
	    console.log(x)
	    if(!this.filters[i](x)){
		return false
	    }
	}
	return true
    },

    do_search: function(e){
	if(e.type == "keypress" && e.which !=13){
	    return;
	}

	this.directory.filter(this.all_filters.bind(this))
    },

    get_filter: function(field, textbox){
        return function(x){	
	    var regex = new RegExp(textbox.val(),'i'); // case insensitive
            if (String(x[field]).search(regex) != -1) return true;
            else return false;
        }.bind(this);	    
    },

    get_teacher_filter: function(textbox){
        return function(x){	
	    var regex = new RegExp(textbox.val(),'i'); // case insensitive
	    teachers = x["teachers"];
	    for (var i = 0; i < teachers.length; i++){
                if (String(teachers[i]["text"]).search(regex) != -1) return true;
	    }
            return false;
        }.bind(this);	    	    
    },

    get_status_filter: function(checkbox){
        return function(x){	
	    console.log(checkbox)
            if (checkbox[0].checked) return true;
            else return x.status == "10";
        }.bind(this);	    	    	
    },

    get_length_filter: function(textbox){
        return function(x){
	    if (textbox.val() != "") {
		if (x["length_hr"] == textbox.val())
		    return true;
		else return false;
	    }
	    return true
        }.bind(this);	    
    },

    get_min_max_filter: function(textbox1, textbox2, attr){
	return function(x){
	    var min = textbox1.val()
	    if (min == "") min = 0
	    var max = textbox2.val()
	    if (max == "") max = Number.MAX_VALUE
	    if (x[attr] >= min && x[attr] <= max)
		    return true;
	    else return false;
        }.bind(this);	    
    
    }
}));
