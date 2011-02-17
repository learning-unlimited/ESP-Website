checkbox_ids = [];

StudentRegInterface = Ext.extend(Ext.TabPanel, {

    reg_instructions: "Welcome to the "+ nice_name+" class lottery registration!<br><br>Instructions:<br><br>Each time slot during "+nice_name+" has its own tab on this page.  You can scroll through the tabs by pressing the arrows on each end of the row of tabs.  For every time slot you want to attend:<br><br>1. Click the tab with the name of that timeslot.  You will see a list of classes.  <i>Note:</i> The tabs will appear at the top of this page.  Please be patient!; particularly on older computers or slower Internet connections, it can take a while for the whole catalog to download into this site and get presented as a catalog.<br><br>2. Select one class to be your \"priority\" class using the circular button on the left. This class is the class you most want to be in during that particular time slot. You do not have to select a priority class, but it is in your best interest to do so, since you have a higher chance of getting into your priority class. We do not guarantee placement into priority classes; we merely give them preferential status in the lottery process, and we expect students to get about 1/3 of their priority classes.<br><br>3. Select as many other classes as you want using the checkboxes. Checking a checkbox says that you are OK with attending this class. If you can’t be placed into your priority class, we will then try to place you into one of these classes. Once again we don’t guarantee placement into these checked classes. It is recommended that you check off at least 8 classes so that you will have a good chance of getting into one of them.<br><br>It is a good idea to have another window or tab in your internet browser open with the catalog and course descriptions for easy reference.<br><a href=\"/learn/"+url_base+"/catalog\" target=\"_blank\">Click here to open the catalog in another window.</a><br><br>Note: Classes with the same name listed under different time slots are the same class, just taught at different times. You are entering the lottery for a specific instance of a class during a specific time slot.<br><br>Finally when you are done with all the timeslots you want to be at "+nice_name+", go to the \"Confirm Registration\" tab and click \"Show me my priority classes!\" You will see a list of classes you flagged.  If those are the classes you want, click \"Confirm Registration.\"  You will be notified by email when results of the lottery are posted.<br><br>For more information on the lottery see the Student Registration FAQ.<br><br>If you don't want to be here, you can <a href='/learn/"+url_base+"/studentreg'>go back to the "+nice_name+" Student Reg page</a>.",

    initComponent: function () {
    
    if (esp_user["cur_grade"])
    {
        grade = esp_user.cur_grade;
        //  console.log("Got user grade: " + grade);
    }
    else
    {
        grade = 0;
        alert("Could not determine your grade!  Please fill out the profile and then return to this page.");
    }

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
	    //width: 800,
	    //height: 450,
	    autoHeight: true,
	    //autoScroll: true,
	    deferredRender: true,
	    //forceLayout: true,
	    closeable: false,
	    tabWidth: 20,
	    enableTabScroll: true,
	    activeTab: 'instructions',
	    monitorResize: true,
	    items: [
	        {
		    title: 'Instructions',
		    xtype: 'panel',
		    items: [
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
 
	this.loadCatalog();
	this.store.load({});	

	Ext.apply(this, Ext.apply(this.initialConfig, config));
	StudentRegInterface.superclass.initComponent.apply(this, arguments); 
    },

    loadPrepopulate: function () {
	    this.oldPreferences = new Ext.data.JsonStore({
		    id: 'preference_store',
		    root: '',
		    fields: [
	            {
			name: 'section_id'
	            },
	            {
			name: 'type'
	            }
		    ],
		    proxy: new Ext.data.HttpProxy({ url: '/learn/'+url_base+'/catalog_registered_classes_json' }),
		    listeners: {
			load: {
			    scope: this,
			    fn: this.prepopulateData
			}
		    }
		});
	    this.oldPreferences.load();
	},
    
    prepopulateData: function (store, records, options) {
	    for (i = 0; i<records.length; i++){
		r = records[i];
		if(r.data.type == 'Interested'){
		    Ext.getCmp(r.data.section_id).setValue(true);
		}
		if(r.data.type == 'Priority/1'){
		    Ext.getCmp('flag_'+r.data.section_id).setValue(true);
		}
	    }
	},

    loadCatalog: function () {
	    this.store =  new Ext.data.JsonStore({
		id: 'store',
	        root: '',
		success: true,
	        fields: [
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
	        } 
		//fields needed for class id generation
		],
		proxy: new Ext.data.HttpProxy({ url: '/learn/'+url_base+'/catalog_json' }),
		listeners: {
		    load: {
			scope: this,
			fn: this.makeTabs
		    }
		}		
	    });
    },
    
    makeTabs: function (store, records, options) {
	    //alert(len(records));
	    //make a tab for each class period
	    //num_tabs and tab_names need to be modified for a particular program
	tabs = [];
	flag_added = [];

	//makes tabs with id = short_description of timeblock
	for(i = 0; i < this.num_tabs; i++)
	    {
		//alert(this.tab_names[i]);
		tabs[this.tab_names[i][0]] = 
		    {
			xtype: 'form',
			id: this.tab_names[i][0],
			title: this.tab_names[i][1],
			items: [],
			height: 800,
			autoScroll: true,
			monitorResize: true,
			listeners: {
			    render: function() { num_opened_tabs++; }
			},
			items: [
		                    {
					xtype: 'fieldset',
					layout: 'column',
					id: this.tab_names[i][1]+'no_class',
					name: this.tab_names[i][1]+'no_class',
					items: 
					[
		                            {
						xtype: 'radio',
						id: 'flag_'+this.tab_names[i][0],
						name: 'flag_'+this.tab_names[i][0]
					    }, 
		                            { 
						xtype: 'displayfield',
						value: "I would not like to flag a priority class for this timeblock."
					    }
				       ]
				    }
                        ]

		    }
	    }
	    //itterate through records (classes)
	    for (i = 0; i < records.length; i++)
	    { 
		r = records[i];
		
		//no walk-in seminars
		if (r.data.category.category != 'Walk-in Seminar'){

		//grade check
		if (r.data.grade_min <= grade && r.data.grade_max >= grade ) {

		num_sections = r.data.get_sections.length;
		//itterate through times a class is offered
		for (j = 0; j < num_sections; j ++)
		{
		    if(r.data.get_sections[j].get_meeting_times.length >0)
		    {
			timeblock = r.data.get_sections[j].get_meeting_times[0];
			//alert()

			//puts id of checkbox in the master list
			checkbox_id = r.data.get_sections[j].id;
			checkbox_ids.push(checkbox_id);

			//comes up with label for checkboxes
			text = '';
			text = text + r.data.category.symbol + r.data.id + ': ' + r.data.title + ', ';
			end_timeblock = r.data.get_sections[j].get_meeting_times[r.data.get_sections[j].get_meeting_times.length-1];
			text = text + timeblock.start.substring(11,16) + ' - ' + end_timeblock.end.substring(11,16);
	
			tabs[timeblock.id].items.push({
				    xtype: 'fieldset',
				    layout: 'column',
				    id: timeblock.short_description+r.data.title,
				    name: timeblock.short_description+r.data.title,
				    items: 
				    [
			               {
					   xtype: 'radio',
					   id: 'flag_'+checkbox_id,
					   name: 'flag_'+timeblock.id,
					   inputValue: r.data.id,
					   listeners: { //listener changes the flagged classes box at the top when the flagged class changes
					       
					   }
				       }, 
			               {
					   xtype: 'checkbox',
					   name: checkbox_id,
					   id: checkbox_id
				       }, 
			               { 
					   xtype: 'displayfield',
					   value: text,
					   autoHeight: true,
					   id: 'title_'+ checkbox_id 
				       }
				    ]
			
			});
		    }
		}
		}//end if for walk in seminars
		}//end if for grade check
	    }
	
	    //adds tabs to tabpanel
	    for (i = 0; i < this.num_tabs; i ++)
	    {
		//alert('add');
		Ext.getCmp('sri').add(tabs[this.tab_names[i][0]]);
	    }

	/*
	    if (grade == 7 || grade == 8){
		for(i = 9; i<=11; i++){
		    Ext.getCmp(this.tab_names[i][0]).hide();
		    Ext.getCmp('sri').hideTabStripItem(this.tab_names[i][0]);
		}
		}*/

	    //creates "confirm registration" tab
	     //creates fields for all first choice classes
	     flagged_classes = [];

	     //adds textarea with some explanation
	     flagged_classes.push({
		     xtype: 'displayfield',
		     height: 80,
		   //width: '600',
		     value: 'To register for the ' + nice_name + ' class lottery, click "Show me my priority classes!"<br><br>  If you like what you see, click "Confirm Registratio."'
	     });

	     //adds "confirm registration" button
	     flagged_classes.push({
		     xtype: 'button',
		     text: 'Show me my priority classes!',
		     handler: this.promptCheck
	     });

	     //adds above to a form
	     Ext.getCmp('sri').add({
		     xtype: 'form',
		     title: 'Confirm Registration',
		     height: 200,
		     items: flagged_classes
		     });
	Ext.getCmp('sri').loadPrepopulate();
     },

    allTabsCheck: function() {
	    if (num_opened_tabs == this.num_tabs){Ext.getCmp('sri').confirmRegistration();}
		    Ext.Msg.show({
			    title: 'Wait!',
			    msg: "You haven't filled out preferences for every time slot.",
			    buttons: {ok:"That's fine.  I won't be at " + nice_name + " for those time slots.", cancel:"No, let me go back and fill out the parts I missed!"},
			    fn: function(button){
				if(button == 'ok') {
				    for(j = 0; j < this.num_tabs; j++) { Ext.getCmp('sri').setActiveTab(i);} 
				    Ext.getCmp('sri').confirmRegistration();
				}
				if(button == 'cancel') { Ext.Msg.hide(); }
			    }
		    });
	},

    promptCheck: function() {
	    flagged_classes = 'Please check to see that these are the classes you intended to flag:<ul>';
	    for(i = 0; i<checkbox_ids.length; i++){
		if (Ext.getCmp('flag_'+checkbox_ids[i]).getValue() == true){
		    title = Ext.getCmp('title_'+checkbox_ids[i]).getValue();
		    flagged_classes = flagged_classes + title + '<ul>';
		}
	    }
	    flagged_classes = flagged_classes + '<br><br><b> After you enter the lottery, remember to finish registering on the main registration page.</b>'
	    Ext.Msg.show({
		    title:  'Priority Classes',
		    msg: flagged_classes,
		    buttons: {ok:'These look good.  Enter me into the ' + nice_name + ' lottery!', cancel:'Wait!  No!  Let me go back and edit them!'},
		    fn: function(button) {
			if (button == 'ok'){Ext.getCmp('sri').allTabsCheck();}
			if (button == 'cancel'){Ext.Msg.hide();}
		    }
		});
    },

     confirmRegistration: function() {
	     tabpanel = Ext.getCmp('sri');
	    //submitForm.getForm().submit({url: 'lsr_submit'})
	     classes = new Object;
	     count = 0;

	     for(i=0; i<checkbox_ids.length; i++) {
		 checkbox = Ext.getCmp(checkbox_ids[i]);
		 classes[checkbox_ids[i]] = checkbox.getValue();
		 flag_id = 'flag_'+checkbox_ids[i];
		 flag = Ext.getCmp(flag_id);
		 classes[flag_id] = flag.getValue();
	     }

	     /*
	     for(i=0; i<flag_ids.length; i++){
	         flag = Ext.getCmp(flag_ids[i]);
		 classes[flag_ids[i]] = flag.getValue();
		 }*/

        var handle_submit_response = function (data) {
            //  console.log("Got response: " + JSON.stringify(data));
            response = Ext.decode(data["responseText"]);
            if (response.length == 0)
            {
                //  console.log("Registration successful.");
                Ext.Msg.show({
                    title:  'Registration Successful',
                    msg: 'Your preferences have been stored in the ESP database and will be used to assign classes in the lottery on Nov. 2.',
                    buttons: {ok:'Continue', cancel:'Return to edit preferences'},
                    fn: function(button) {
                        if (button == 'ok') 
                        {
                            window.location.href = '/learn/'+url_base+'/confirmreg';
                        }
                        if (button == 'cancel') {Ext.Msg.hide();}
                    }
                });
            }
            else
            {
                //  console.log("Registration unsuccessful: " + JSON.stringify(response));
                msg_list = 'Some of your preferences have been stored in the ESP database.  Others caused problems: <br />';
                for (var i = 0; i < response.length; i++)
                {
                    if (response[i].emailcode)
                        msg_list = msg_list + response[i].emailcode + ': ' + response[i].text + '<br />';
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
        };

	     data = Ext.encode(classes);
	     Ext.Ajax.request({
		     url: 'lsr_submit',
             success: handle_submit_response,
		     params: {'json_data': data},
		     method: 'POST'
		 });
    }
});

Ext.reg('lottery_student_reg', StudentRegInterface);


var win;
Ext.onReady(function() {
win = new Ext.Panel({
  renderTo: Ext.get("reg_panel"),
      //	closable: false,
      monitorResize: true,
      items: [{ xtype: 'lottery_student_reg', 
	  id: 'sri'
	  }],
      title: nice_name + ' Class Lottery - ' + esp_user["cur_first_name"] + ' ' + esp_user["cur_last_name"] + ' (grade ' + esp_user["cur_grade"] + ')',
      autoWidth: true,
      autoHeight: true
      });


    win.show();
    //submitForm.getForm().submit({url: 'lsr_submit'});
});
