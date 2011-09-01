checkbox_ids = [];
var checkbox_ids_by_timeblock = new Array();

var instructions = "Welcome to the "+ nice_name+" class lottery registration!<br><br>";
if (priority_limit == 1) {
    instructions += "Instructions:<br><br>Each time slot during "+nice_name+" has its own tab on this page.  You can scroll through the tabs by pressing the arrows on each end of the row of tabs.  For every time slot you want to attend:<br><br>1. Click the tab with the name of that timeslot.  You will see a list of classes.  <i>Note:</i> The tabs will appear at the top of this page.  Please be patient!; particularly on older computers or slower Internet connections, it can take a while for the whole catalog to download into this site and get presented as a catalog.<br><br>2. Select one class to be your \"priority\" class using the circular button on the left. This class is the class you most want to be in during that particular time slot. You do not have to select a priority class, but it is in your best interest to do so, since you have a higher chance of getting into your priority class. We do not guarantee placement into priority classes; we merely give them preferential status in the lottery process, and we expect students to get about 1/3 of their priority classes.<br><br>3. Select as many other classes as you want using the checkboxes. Checking a checkbox says that you are OK with attending this class. If you can’t be placed into your priority class, we will then try to place you into one of these classes. Once again we don’t guarantee placement into these checked classes. It is recommended that you check off at least 8 classes so that you will have a good chance of getting into one of them.<br><br>It is a good idea to have another window or tab in your internet browser open with the catalog and course descriptions for easy reference.<br><a href=\"/learn/"+url_base+"/catalog\" target=\"_blank\">Click here to open the catalog in another window.</a><br><br>Note: Classes with the same name listed under different time slots are the same class, just taught at different times. You are entering the lottery for a specific instance of a class during a specific time slot.<br><br>Finally when you are done with all the timeslots you want to be at Splash, go to the \"Confirm Registration\" tab and click \"Show me my priority classes!\" You will see a list of classes you flagged.  If those are the classes you want, click \"Confirm Registration.\"  You will be notified by email when results of the lottery are posted.<br><br>For more information on the lottery see the <a href=\"/learn/lotteryFAQ.html\">Student Registration FAQ<\a>.<br><br>If you don't want to be here, you can <a href='/learn/"+url_base+"/studentreg'>go back to the "+nice_name+" Student Reg page</a>."
}
else {
    instructions += "<font size = 4><font color='firebrick'> <center><b>"+nice_name+" Lottery Instructions<br />Please take a moment to read this in its entirety</b></center></font></font>";

instructions += "<p><br />Registration should be completed by <b><u>students</u></b>. Parents, please allow your children to choose their own classes.<br /><br />";

instructions += "<b>Give the page a moment to load</b>. You will know that it is fully loaded once you see five blue tabs appear at the top of the window. If you only see one tab, wait for the rest to appear before continuing.<br /><br />";

instructions += "The five tabs should say 'Instructions', '10-12', '1-2:30', '2:30-4:00', and 'Confirm Registration'. The three middle tabs refer to each of the three timeblocks, respectively. Clicking on one of them will display all of the classes available to you during that timeblock.<br /><br />";

instructions += "Each class has a drop-down menu associated with it. Use this to select your three preferences for the timeblock. So you should label your top choice class with '1', your second choice class with '2', and your third choice class with '3'. All other classes should be labeled with 'none'. You may pick up to three classes in each timeblock, for a total of nine classes. It is to your advantage to pick nine classes, since you might not get into all of your top choice classes.<br /><br />";

instructions += "Once you have selected your nine classes, click on the 'Confirm Registration' tab. Press the button that appears on that page. A message should pop up showing the classes that you selected. Check to make sure that they are correct; if they are, press 'Enter me in the lottery'. Then this information will be stored in the database, and you will be redirected back to the student registration page.<br /><br />"

instructions += "<b>Some classes have application questions associated with them!</b> If you select any application question classes, you will be redirected to a page that lists all the questions. You should fill out any and all questions that appear. <b>If you don't fill them out, you won't be eligible for any application question classes!</b>";
    
}

StudentRegInterface = Ext.extend(Ext.TabPanel, {
    
    reg_instructions: instructions,

    initComponent: function () 
    {
    
        Ext.Ajax.request({
    	    url: '/learn/'+url_base+'/timeslots_json',
    	    success: function (response, opts) {
    		//alert('opts '+ opts);
    		//alert('response '+response);
    		rt = Ext.decode(response.responseText);
    		this.tab_names = rt;
    		this.num_tabs = this.tab_names.length;
    	    },
    	    scope: this
        });
    
        num_opened_tabs = 0;
    
    	var config = {
    	    id: 'sri',
    	    autoHeight: true,
    	    deferredRender: true,
    	    closeable: false,
    	    tabWidth: 20,
    	    enableTabScroll: true,
    	    activeTab: 'instructions',
    	    monitorResize: true,
    	    items: 
            [
    	        {
        		    title: 'Instructions',
        		    xtype: 'panel',
        		    items: 
                    [
    	                {
            			    xtype: 'displayfield',
            			    //height: 600,
            			    autoHeight: true,
            			    value: this.reg_instructions,
            			    preventScrollbars: true
            			}
            	    ],
        		    id: 'instructions'
        		}
            ]
    	};
     
        this.loadPrepopulate();
    	this.loadCatalog();
    	this.store.load({});	

    	Ext.apply(this, Ext.apply(this.initialConfig, config));
    	StudentRegInterface.superclass.initComponent.apply(this, arguments); 
    },

    loadPrepopulate: function () {
	    Ext.getCmp("sri").oldPreferences = new Ext.data.JsonStore({
		    id: 'preference_store',
		    root: '',
		    fields: 
            [
	            {
        			name: 'section_id'
	            },
	            {
	        		name: 'type'
  	            }
		    ],
		    proxy: new Ext.data.HttpProxy({ url: '/learn/'+url_base+'/catalog_registered_classes_json' }),
		});
	    this.oldPreferences.load();
	},

    loadCatalog: function () {
	    this.store =  new Ext.data.JsonStore({
		id: 'store',
	        root: '',
		success: true,
	        fields: 
            [
    	        {
        		    name: 'id'
        		},  
        		{
                    name: 'title'
                },
                {
                    name: 'grade_max'
                },
                {
                    name: 'grade_min'
                },
    	        {
        		    name: 'get_sections'
    	        },
    	        {
        		    name: 'category'
        		},
    	        {
        		    name: 'description'
    	        },
    	        {
        	        name: 'num_questions'
    	        }
		//fields needed for class id generation
    		],
    		proxy: new Ext.data.HttpProxy({ url: '/learn/'+url_base+'/catalog_json' }),
    		listeners: 
            {
    		    load: {
        			scope: this,
        			fn: this.makeTabs
    		    }
    		}		
	    });
    },
    
    makeTabs: function (store, records, options) {
	    //make a tab for each class period
	    //num_tabs and tab_names need to be modified for a particular program
    	tabs = [];
        classLists = [];
    	flag_added = [];

	    //itterate through records (classes)
    	for (i = 0; i < records.length; i++)
       	{ 
	    	r = records[i];    	
		    //no walk-in seminars
		    if (r.data.category.category == 'Walk-in Seminar'){
                //will put in clever stuff for displaying walk-ins here                
                continue;
            }

		    //grade check
		    if (r.data.grade_min >= grade || r.data.grade_max <= grade ) {
                continue;
            }

    		num_sections = r.data.get_sections.length;
	    	//itterate through times a class is offered
	    	for (j = 0; j < num_sections; j ++)
	    	{
	    	    if(r.data.get_sections[j].get_meeting_times.length >0)
	    	    {
	    		    timeblock = r.data.get_sections[j].get_meeting_times[0];
                    if(!classLists[timeblock.id]){
                        classLists[timeblock.id] = []
                    }
                    classLists[timeblock.id].push(r);                    
                }
            }
	    }

        console.log(this.oldPreferences);

    	//makes tabs with id = short_description of timeblock
    	for(i = 0; i < this.num_tabs; i++) 
        {
    		//alert(classLists[this.tab_names[i][0]].length);
    		this.add( new TimeslotPanel(
		    {
    			xtype: 'timeslotpanel',
    			id: this.tab_names[i][0],
    			title: this.tab_names[i][1],
                ESPclasses: classLists[this.tab_names[i][0]],
                timeblock: this.tab_names[i],
                oldPreferences: this.oldPreferences
	        }));
	    }

	    // this will be needed later, when making dropdown boxes
	    var dropdown_states_data = [];
	    dropdown_states_data.push(['0','none']);
        for (i = 1; i <= priority_limit; ++i) {
            dropdown_states_data.push([String(i),String(i)]);
        }
		this.addConfirmTab();
     },

    addConfirmTab: function () 
    {
	     Ext.getCmp('sri').add({
             id: "confirm",
		     xtype: 'form',
		     title: 'Confirm Registration',
             listeners: {
                show: this.getPreferences
             },

		 });
    },

    getPreferences: function () {
        confirmPanel = Ext.getCmp("confirm");
        confirmPanel.removeAll();
        confirmPanel.add(
                {
		            xtype: 'displayfield',
		            height: 40,
		            value: '<font size=3">To register for the ' + nice_name + ' class lottery, click "Show me my priority classes!" and then, if everything appears correct, press "Enter me in the lottery!"</font>'//<br><br>  If you like what you see, click "Show me my priority classes!"'
	            });
        confirmPanel.add({
	    	        xtype: 'button',
    		        text: 'Enter my preferences in the Splash! Lottery',
	    	        handler: Ext.getCmp("sri").allTabsCheck,
                    scope: Ext.getCmp("sri")
	            });

        for(k = 1; k < Ext.getCmp("sri").items.items.length; k++){
            var tab = Ext.getCmp("sri").items.items[k];
            if(tab.xtype == "timeslotpanel"){
                confirmPanel.add({
                    xtype: "displayfield",
                    value: tab.getSummary()
                });  
            }
        }
        confirmPanel.doLayout();
        return;
    },

    allTabsCheck: function() {
        var missing = false;
        for(i = 0; i < this.items.items.length; i++)
        {
            tab = this.items.items[i];
            if(tab.xtype == "timeslotpanel")
            {
                if(!tab.timeslotCompleted())
                {
                    missing = true;
                    break;
                }
            }
        }
        if (missing) {
            Ext.Msg.show({
                title: 'Wait!',
                msg: "You haven't filled out preferences for every time slot.",
                buttons: {ok:"That's fine.  I won't be at " + nice_name + " for those time slots.", cancel:"No, let me go back and fill out the parts I missed!"},
                fn: function(button){
                    if(button == 'ok') {
                        Ext.getCmp('sri').confirmRegistration();
                    }
                    if(button == 'cancel') { Ext.Msg.hide(); }
                }
            });
        }
        else {  Ext.getCmp('sri').confirmRegistration();  }
	},

     confirmRegistration: function() {
	     tabpanel = Ext.getCmp('sri');
	    //submitForm.getForm().submit({url: 'lsr_submit'})
        if(priority_limit == 1)
        {
            var ESPclasses = new Object();
            for(i = 1; i < tabpanel.items.items.length; i++)
            {
                var tab = tabpanel.items.items[i];
                if(tab.xtype == 'timeslotpanel')
                {
                    var tabPreferences = tab.getNewPreferences();
                    for(var preference in tabPreferences)
                    {
                        ESPclasses[preference] = tabPreferences[preference];
                    }
                }
            }
        }
        else {
            for(i = 0; i < this.num_tabs; i++) {
                var ids = checkbox_ids_by_timeblock[this.tab_names[i][0]].split('_');
                //alert(ids);
                for (j = 0; j < ids.length - 1; ++j) {
                    if (val = parseInt(Ext.getCmp("combo_"+ids[j]).getValue())) {
		                ESPclasses[ids[j]] = new Array(val, this.tab_names[i][0]);
		                //alert(classes[ids[j]]);
		            }
                }
            }    
        }

        var handle_submit_response = function (data) {
            //  console.log("Got response: " + JSON.stringify(data));
            response = Ext.decode(data["responseText"]);
            if (response.length == 0)
            {
                //  console.log("Registration successful.");
                Ext.Msg.show({
                    title:  'Registration Successful',
                    msg: 'Your preferences have been stored in the ESP database and will be used to assign classes in the lottery.',
                    buttons: {ok:'Continue'},
                    fn: function(button) {
                        if (button == 'ok') 
                        {
                            window.location.href = '/learn/'+url_base+'/studentreg';
                        }
                    }
                });
            }
            else
            {
                //  console.log("Registration unsuccessful: " + JSON.stringify(response));
                if (response[0].doubled_priority) {
                    alert("You assigned multiple classes to have the same priority in the same timeblock. Please fix this.");
                }
                else {
                    msg_list = 'Some of your preferences have been stored in the ESP database.  Others caused problems: <br /><br />';
                    for (var i = 0; i < response.length; i++)
                    {
                        if (response[i].emailcode) {
                            msg_list = msg_list + response[i].emailcode + ': ' + response[i].text + '<br />';
                        }
                    }
                    Ext.Msg.show({
                        title:  'Registration Problems',
                        msg: msg_list,
                        buttons: {ok: 'Return to edit preferences'},
                        fn: function(button) {
                            Ext.Msg.hide();
                        }
                    });
                }
            }
        };
         //console.log(ESPclasses);
	     data = Ext.encode(ESPclasses);
        //console.log(data);
	     Ext.Ajax.request({
		     url: '/learn/'+url_base+'/lsr_submit',
		     success: handle_submit_response,
		     failure: function() {
		        alert("There has been an error on the website. Please contact esp@mit.edu to report this problem.");
		     },
		     params: {'json_data': data, 'url_base': url_base},
		     method: 'POST',
		     headers: {'X-CSRFToken': Ext.util.Cookies.get('csrftoken')}
		 });
    }
});

Ext.reg('lottery_student_reg', StudentRegInterface);


var win;
Ext.onReady(function() {
win = new StudentRegInterface({
  renderTo: Ext.get("reg_panel"),
      //	closable: false,
      monitorResize: true,
      id: "sri",
      title: nice_name + ' Class Lottery - ' + esp_user["cur_first_name"] + ' ' + esp_user["cur_last_name"] + ' (grade ' + grade + ')',
      autoWidth: true,
      autoHeight: true
      });


    win.show();
    //submitForm.getForm().submit({url: 'lsr_submit'});
});
