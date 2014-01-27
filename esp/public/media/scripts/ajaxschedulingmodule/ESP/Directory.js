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
        
            // get header
            this.header = $j("#directory-table-header")

	    //TODO:  set up sorting
            $j.each(this.properties, function(key, prop){
                var td = $j("#directory-header-"+key).addClass(prop.css)
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

            css: "td_id"
        },
        'Title': {
            get: function(x){ return x.text; },
            sort: function(x,y){
                return cmp(x.section.text, y.section.text);
            },
	    // css: 'width:400px;'
            css: "td_title"
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
            css: "td_teacher"
        },
        'Length': {
            get: function(x) { return x.length_hr; },
            sort: function(x,y) {
                return x.section.length - y.section.length;
            },
            css: "td_length"
          }
        },
        
        // filter active rows
        filter: function(filter){
            var filter = filter || this.activeFilter || function(){ return true; };
            this.activeFilter = filter;
            var active_rows = [];
            $j.each(this.entries, function(i,entry){
                if (filter(entry.section))
                    active_rows.push(entry);
            });
            this.active_rows = active_rows;
            this.sort();
        },

        // filter for determining active section or not
        activeFilter: function(section) {
	    var lunch_symbol = "";
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
        },
        
        // update directory entries
        update: function(){
	    tbody = $j("#directory-table-body")[0]
            tbody.hide();
            tbody.innerHTML = "";
            $j.each(
		this.active_rows, function (i,x){ 
		    this.table.append(x.update().el); 
		    x.draggable(); 
		}.bind(this)
	    );
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
                var td = $j('<td></td>').addClass(prop.css);
		td.append(prop.get(section));
		if (section.status != 10){
		    td.addClass("unapproved")
		}
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

/* State of the art:  the current design is simple to understand but
not very high performance.  It runs every filter on every class every time 
filters run.  Right now for an HSSP this takes less than a second.  It needs to 
be tested on MIT Splash size data, and possibly optimized there.  

It also may be refactored when a quick search box appears.
*/
ESP.declare('ESP.Scheduling.Widgets.SearchBox', Class.create({
    //QUESTION:  is grabbing the textbox every time a noticeable performance problem?
    //QUESTION:  what does .bind do?
     initialize: function(directory) {
	 this.filters = [
	     //id
	     function(x){
		 //TODO:  make this support sections numbers like X6034s1
		 var textbox = $j("#filter_ID")
		 var regex = new RegExp(textbox.val(),'i'); // case insensitive
		 var class_code = x.category + x.class_id
		 return (String(class_code).search(regex) != -1)
             }.bind(this),
	     //title
	     function(x){
		 var textbox = $j("#filter_Title")
		 var regex = new RegExp(textbox.val(),'i'); // case insensitive
		 return (String(x.text).search(regex) != -1)
             }.bind(this),
	     //teacher 
	     function(x){
		 if ($j("#filter_Teacher").val() == ""){
		     //this is important.  If there is no text in the teacher filter, classes with no teacher listed
		     //don't show up without this clause.
		     //Most fields can't be blank, but we have blank teacher fields in production
		     return true;
		 }
		 var regex = new RegExp($j("#filter_Teacher").val(),'i'); // case insensitive
		 teachers = x["teachers"];
		 for (var i = 0; i < teachers.length; i++){
                     if (String(teachers[i]["text"]).search(regex) != -1) return true;
		 }
		 return false;
             }.bind(this),
	     //timeslot
	     function(x){
		 if ($j("#filter_Timeslot").val() == ""){
		     return true;
		 }
		 var searchby = $j("#filter_Timeslot").val();
		 teachers = x["teachers"];
		 for (var i = 0; i < teachers.length; i++){
		 	var isTeacherAvailable = false;

			// check for availability
		 	for(var j = 0; j < teachers[i].available_times.length; j++) {
		 		if(teachers[i].available_times[j] !== undefined) {
			 		j_timeslot = teachers[i].available_times[j].text;
			 		if(j_timeslot !== undefined && (j_timeslot.indexOf(searchby) != -1 || searchby.indexOf(j_timeslot) != -1)) {
			 			isTeacherAvailable = true;
			 		}
		 		}
		 	}

		 	// check for conflicts
		 	for(var j = 0; j < teachers[i].sections.length; j++) {
		 		if(teachers[i].sections[j] !== undefined && teachers[i].sections[j].blocks !== undefined) {
		 			for(var k = 0; k < teachers[i].sections[j].blocks.length; k++) {
		 				if(teachers[i].sections[j].blocks[k] !== undefined) {
		 					k_timeslot = teachers[i].sections[j].blocks[k].time.text;
					 		if(k_timeslot !== undefined && (k_timeslot.indexOf(searchby) != -1 || searchby.indexOf(k_timeslot) != -1)) {
					 			isTeacherAvailable = false;
			 				}
		 				}
		 			}
		 		}
		 	}

		 	if(!isTeacherAvailable) return false;
		 }
		 return true;
             }.bind(this),
	     //class size
	     function(x){
		 var min = $j("#filter_Min-size").val()
		 if (min == "") min = 0
		 var max = $j("#filter_Max-size").val()
		 if (max == "") max = Number.MAX_VALUE
		 if (x["class_size_max"] >= min && x["class_size_max"] <= max)
		     return true;
		 else return false;
             }.bind(this),
	     //length
	     //TODO:  change all the xs to "section" which is actually descriptive
	     function(x){
		 var min = $j("#filter_Min-length").val()
		 if (min == "") min = 0
		 var max = $j("#filter_Max-length").val()
		 if (max == "") max = Number.MAX_VALUE
		 if (x.length_hr >= min && x.length_hr <= max)
		     return true;
		 else return false;
             }.bind(this),
	     //show rejected
	     function(x){
		 //QUESTION  how can I make jquery return just one and not a list
		 if ($j("#filter_Status")[0].checked) return true;
		 else return x.status == "10";
             }.bind(this),
	     //show scheduled classes
	     function(x){
		 //TODO:  styling for scheduled classes
		 if ($j("#filter_Scheduled")[0].checked) return true;
		 else return x.blocks.length == 0;
	     }.bind(this)
	 ]
	 $j('#directory-accordion').bind("accordionchange", this.do_search.bind(this))
         this.directory = directory;
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

    do_search: function(){
	this.directory.filter(this.all_filters.bind(this))
    },
}));
