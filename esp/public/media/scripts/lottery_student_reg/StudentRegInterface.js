checkbox_ids = [];
var checkbox_ids_by_timeblock = new Array();

StudentRegInterface = Ext.extend(Ext.TabPanel, {

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
		    autoHeight: true,
                    items: 
                    [
                        {
                            xtype: 'displayfield',
                            //height: 600,
                            autoHeight: true,
                            value: instructions_text,
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
            proxy: new Ext.data.HttpProxy({ url: '/learn/'+url_base+'/catalog_registered_classes_json' })
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
                    name: 'teachers'
                },
                {
                    name: 'class_size_max'
                },
                {
                    name: 'category'
                },
                {
                    name: 'class_info'
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
        walkinLists = [];
        flag_added = [];
	var num_sections = 0;

        //itterate through records (classes)
        for (i = 0; i < records.length; i++)
        { 
            r = records[i];        

	    //  Prepopulate walk-in and class lists
	    num_sections = r.data.get_sections.length;
	    for (var j = 0; j < num_sections; j++)
	    {
		if (r.data.get_sections[j].get_meeting_times.length > 0)
		{
                    for (var k = 0; k < r.data.get_sections[j].get_meeting_times.length; k++)
                    {
		        if (!(r.data.get_sections[j].get_meeting_times[k].id in walkinLists))
			    walkinLists[r.data.get_sections[j].get_meeting_times[k].id] = [];
		        if (!(r.data.get_sections[j].get_meeting_times[k].id in classLists))
			    classLists[r.data.get_sections[j].get_meeting_times[k].id] = [];
                    }
		    //if (!(r.data.get_sections[j].get_meeting_times[0].id in walkinLists))
			//walkinLists[r.data.get_sections[j].get_meeting_times[0].id] = [];
		    //if (!(r.data.get_sections[j].get_meeting_times[0].id in classLists))
			//classLists[r.data.get_sections[j].get_meeting_times[0].id] = [];
		}
	    }

            //no walk-in seminars
            if (r.data.category.category == 'Walk-in Seminar'){
                this.addSectionsToList(r, walkinLists);                
                continue;
            }
 
            //grade check
            if (r.data.grade_min > grade || r.data.grade_max < grade ) {
                continue;
            }

	    //   console.log("Adding " + r.data.id + " to class lists");
            this.addSectionsToList(r, classLists);
        }

        //console.log(walkinLists);

        //makes tabs with id = short_description of timeblock
        for(i = 0; i < this.num_tabs; i++) 
        {
	    //9 and 11 are hardcoded for Splash 2011.  AFAIK there's no general way to tell whether a block is high school only?  Will look into this later
            if(i >= 9 && i <= 11 && grade < 9){
                continue;
            }
            //alert(classLists[this.tab_names[i][0]].length);
            this.add( new TimeslotPanel(
            {
                xtype: 'timeslotpanel',
                id: this.tab_names[i][0],
                title: this.tab_names[i][1],
                ESPclasses: classLists[this.tab_names[i][0]],
                ESPwalkins: walkinLists[this.tab_names[i][0]],       
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

    addSectionsToList: function (ESPClass, lists)
    {
        num_sections = ESPClass.data.get_sections.length;
        //itterate through times a class is offered
        for (j = 0; j < num_sections; j ++)
        {
            if(ESPClass.data.get_sections[j].get_meeting_times.length >0)
            {
                if(ESPClass.data.category.category == 'Walk-in Seminar')
                {
                    for (k = 0; k < ESPClass.data.get_sections[j].get_meeting_times.length; k++)
                    {
                        timeblock = ESPClass.data.get_sections[j].get_meeting_times[k];
                        /*if(!lists[timeblock.id]){
                            lists[timeblock.id] = []
                        }
		        */
		
                        lists[timeblock.id].push(ESPClass);
                    }
                }
                else
                {
                    timeblock = ESPClass.data.get_sections[j].get_meeting_times[0];
                    /*if(!lists[timeblock.id]){
                        lists[timeblock.id] = []
                    }
		    */
		
                    lists[timeblock.id].push(ESPClass);
                }
            }
	    else
	    {
		//  console.log("Warning, no meeting times for " + ESPClass.data.id);
	    }
        }
    },  

    addConfirmTab: function () 
    {
         Ext.getCmp('sri').add({
             id: "confirm",
             xtype: 'form',
             title: 'Confirm Registration',
	     autoHeight: true,
             listeners: {
                show: this.getPreferences
             }
         });
    },

    getPreferences: function () {
        confirmPanel = Ext.getCmp("confirm");
        confirmPanel.removeAll();
        confirmPanel.add(
                {
                    xtype: 'displayfield',
                    height: 40,
                    value: confirm_text
                });
        confirmPanel.add({
                    xtype: 'button',
                    text: enter_lottery_text,
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
                msg: missing_timeblocks_text,
                buttons: {ok: missing_timeblocks_continue_text, cancel: missing_timeblocks_goback_text},
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
                    title:  registration_successful_title_text,
                    msg: registration_successful_text,
                    buttons: {ok:'Continue'},
                    fn: function(button) {
                        if (button == 'ok') 
                        {
                            window.open('/learn/'+url_base+'/confirmreg','_blank');
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

         data = Ext.encode(ESPclasses);

	 Ext.Ajax.timeout = 300000;  // Just in case the server is really totally hosed
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
      //    closable: false,
      monitorResize: true,
      id: "sri",
      title: nice_name + ' Class Lottery - ' + esp_user["cur_first_name"] + ' ' + esp_user["cur_last_name"] + ' (grade ' + grade + ')',
      autoWidth: true,
      autoHeight: true
      });


    win.show();
    //submitForm.getForm().submit({url: 'lsr_submit'});
});

