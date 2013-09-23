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
            this.table = $j(".directory");
        
            // create header
            this.header = $j("#directory-table-header")

	    //TODO:  set up sorting
            $j.each(this.properties, function(key, prop){
                var td = $j("#directory-header-"+key)
                prop.header = td;
                if (prop.sort) {
                    // enable onclick sorting
                    td.bind('click', function(e){
                        prop.reverse = (directory.active_sort != prop) ? prop.reverse : !prop.reverse;
                        directory.sort(prop);
                    });
                }
            });
        
            // add sections
            this.addEntry(sections, false);
            this.filter();
        },
        

        //TODO:  code to style unapproved (and scheduled classes so that it's not repeated for every column
        // table columns
        properties: {
        'ID': {
            get: function(x){ return x.block_contents.clone(true); },
            sort: function(x,y){
                // use code instead of emailcode; that's how Scheduling.process_data names it
                var diff = x.section.class_id - y.section.class_id;
                return diff == 0 ? cmp(x.section.code, y.section.code) : diff;
            },

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
	    tbody = $j("#directory-table-body")
            tbody.hide();
            tbody.innerHTML = "";//.children().remove();  // The 'right' way here is vastly slower, sadly.  -- aseering 10/23/2010
            $j.each(this.active_rows, function (i,x){ tbody.append(x.update().el); x.draggable(); }.bind(this));
            tbody.show();
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
	    
            this.tds = {};
            $j.each(this.directory.properties,function(index, prop){
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

	//add filters to filter box
	//TODO:  bind search to keypres for all inputs
	//title and id
	this.filters = []
	this.filters.push(this.get_filter("Title", $j("#filter_Title"), "text"))   
	this.filters.push(this.get_filter("Id", $j("#filter_ID"), "text"))   
	this.filters.push(this.get_teacher_filter($j("#filter_Teacher")))
	this.filters.push(this.get_status_filter($j("#filter_Status")))
	//input.bind('change', this.do_search.bind(this))

	this.directory.filter(this.all_filters.bind(this))
    },

    all_filters: function(x){
	for (var i=0; i < this.filters.length; i ++){
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
            if (checkbox.checked) return true;
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
