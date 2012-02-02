//the following is temporary sample data until json queries are actually constructed

/**    timeslots: map (id) -> JS object with attributes id, label, start, end, sections (list of IDs)
       sections: map (id) -> JS object with attributes id, emailcode, title, timeslots (sorted list of IDs), grade_min, grade_max, capacity, num_students, lottery_priority, lottery_interested **/

timeslots = {1:  
	     {
		 id: 1, 
		 label: "Sat 9-10",
		 sections: [1, 2]  
	     },

	     2:
	     {
		 id: 2,
		 label: "Sat 10-11",
		 sections: [3, 4]
	     }
         }

sections = {
    1:
    {
	id: 1,
	emailcode: "M1234",
	    title: "A two-slot math class",
	    timeslots: [1, 2],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: false,
	    lottery_interested: false
    },

 2:
    {
	id: 2,
	emailcode: "M1235",
	    title: "A one-slot math class, 9-12",
	    timeslots: [1],
	    grade_min: 9,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: false,
	    lottery_interested: false
	    },
 3:
    {
	id: 3,
	emailcode: "A2222",
	    title: "An arts class iwth interest",
	    timeslots: [2],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: false,
	    lottery_interested: true
	    },
 4:
    {
	id: 4,
	emailcode: "A3333",
	    title: "An arts class with priority",
	    timeslots: [2],
	    grade_min: 7,
	    grade_max: 12,
	    capacity: 20,
	    num_students: 0,
	    lottery_priority: true,
	    lottery_interested: false
    }
}

$j(document).ready(function() { 
    /**$.getJSON({
       '/learn/Spark/2011/timeslots_json/',
       function(data){
          $j("#content").append( "<p> HI! </p>");
	  }
    });**/
	show_app(timeslots);
});              

show_app = function(timeslots){
    //should display a list of timeslots as hyperlinks 
    //and some instructions in a div that we will replace with checkboxes

    //table_content = '<table id="timeslot_list" style="text-align: center" align="center" width="400"></table>'
    table_row = '<a href="" onclick="show_timeslot(%ID%)">%LABEL%</a><br>'
 
    //adds timeslot links to table
    for(id in timeslots){
	t = timeslots[id]
	new_table_row = table_row.replace("%ID%", t.id).replace("%LABEL%", t.label); 
	$j("#timeslot_list").append(new_table_row);
    }
};

show_timeslot = function(id){
    t = timeslots(id);
    
};

