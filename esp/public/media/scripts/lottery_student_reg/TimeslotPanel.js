TimeslotPanel = Ext.extend(Ext.FormPanel, { 
    //xtype: 'form',
    items: [],
    height: 800,
    priorityLimit: 1,
    autoScroll: true,
    monitorResize: true,
    listeners: { 
        render: this.makeCheckBoxes,
        //beforehide: this.checkPriorities
    },

    makeCheckBoxes: function() {
        for(i = 0; i < classes.length; i++){
            var espClass = classes[i];
			checkbox_id = r.data.get_sections[i].id;
	    	checkbox_ids.push(checkbox_id);

		    //comes up with label for checkboxes
		    text = '';
		    text = text + r.data.category.symbol + r.data.id + ': ' + r.data.title + ', ';
		    end_timeblock = r.data.get_sections[j].get_meeting_times[r.data.get_sections        [j].get_meeting_times.length-1];
		    text = text + timeblock.start.substring(11,16) + ' - ' + end_timeblock.end.substring(11,16);
        
            if (priority_limit == 1) 
            {
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
            else 
            {
                new_column = 
                {
		                xtype: 'fieldset',
		                layout: 'column',
		                id: 'column_'+checkbox_id,
		                name: timeblock.short_description+r.data.title,
		                items: []
                }

                new_column.items.push({
                    xtype: 'combo',
                    hiddenName: 'priority_' + checkbox_id,
                    hiddenID: 'priority_' + checkbox_id,
                    id: 'combo_' + checkbox_id,
                    name: 'combo_' + checkbox_id,
                    store: dropdown_states_data,
                    queryMode: 'local',
                    submitValue: true,
                    width: 70,
                    editable: false,
                    triggerAction: 'all',
                    value: '0'
                });

                var keys = [];
                for (var key in r.data) {
                    keys.push(key);
                }
                if (r.data.num_questions) {
                    text += " <b>(this class has " + r.data.num_questions + " application question";
                    if (r.data.num_questions > 1) {
                        text += "s";
                    }
                    text += ")</b>"
                }
                new_column.items.push({
                    xtype: 'displayfield',
                    value: " &nbsp; &nbsp; &nbsp; &nbsp; " + text,
                    autoHeight: true,
                    id: 'title_'+ checkbox_id 
	            });
	            tabs[timeblock.id].items.push(new_column)
	            checkbox_ids_by_timeblock[timeblock.id] += (checkbox_id+"_");
            }
        }
        addNoPreferenceCheckbox;
    },

    initComponent: function() { 
  //      var config = {};
	//    Ext.apply(this, Ext.apply(this.initialConfig, config));
	    TimeslotPanel.superclass.initComponent.apply(this, arguments);
    },

    //allerts the user if they assigned multiple classes the same priority
    //add warning if no priority is marked?
    checkPriorities: function() {
	    var priorities = new Array(priorityLimit + 1);
        for(i=0; i <= priorityLimit; ++i) {
	        priorities[i] = 0;
	    }
        var ids = checkbox_ids_by_timeblock[tab.getId()].split('_');
        for(i=0; i < ids.length - 1; ++i) {
            //if (++priorities[parseInt(tab.items[i].items[0].getValue())] > 1) {
			if (parseInt(Ext.getCmp("combo_"+ids[i]).getValue()) 
                        && ++priorities[Ext.getCmp("combo_"+ids[i]).getValue()] > 1) {
			    alert("You assigned multiple classes to have the same priority. Please fix this.");
			    tab.show();
                return false;
			}
         }
         return true;
    },

    addNoPreferenceCheckbox: function () {
        alert("addNoPreferenceCheckbox");
		if (priority_limit == 1) {
            alert("hello");
		    tabs[this.tab_names[i][0]].items.push(
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
		    });
        }
    }
});

Ext.reg('timeslot_panel', TimeslotPanel);
