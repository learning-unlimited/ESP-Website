TimeslotPanel = Ext.extend(Ext.FormPanel, {

    ESPclasses: [],
    timeblock: [],

    initComponent: function() {
        var config =
        {
            items:
            {
                xtype: 'fieldset',
                layout: 'column',
                id: this.id+'no_class',
                name: this.id+'no_class',
                items: 
                [
                    {
                        xtype: 'radio',
	                    id: 'flag_'+this.id,
	                    name: 'flag_'+this.id
                    },{ 
	                    xtype: 'displayfield',
	                    value: "I would not like to flag a priority class for this timeblock."
                    }
                ]
            },
            height: 800,
            priorityLimit: 1,
            autoScroll: true,
            monitorResize: true,
            listeners: { 
                render: this.makeCheckBoxes,
                //beforehide: this.checkPriorities
            }
        };

    	Ext.apply(this, Ext.apply(this.initialConfig, config));
        TimeslotPanel.superclass.initComponent.apply(this, arguments); 
    },

    makeCheckBoxes: function() {
        for(i = 1; i < this.ESPclasses.length; i++)
        {
            var r = this.ESPclasses[i];

		    //comes up with label for checkboxes
		    text = '';
		    text = text + r.data.category.symbol + r.data.id + ': ' + r.data.title + ', ';
		    //end_timeblock = r.data.get_sections[j].get_meeting_times[r.data.get_sections[j].get_meeting_times.length-1];
		    //text = text + timeblock.start.substring(11,16) //+ ' - ' + end_timeblock.end.substring(11,16);
        
            if (priority_limit == 1) {
		        this.add({
		            xtype: 'fieldset',
		            layout: 'column',
		            id: timeblock[0] + r.data.title,
		            name: timeblock[1] + r.data.title,
		            items: 
		            [
	                       {
    					       xtype: 'radio',
            			       id: 'flag_'+r.data.id,
            			       name: 'flag_'+timeblock[0],
            			       inputValue: r.data.id,
            			       listeners: { //listener changes the flagged classes box at the top when the flagged class changes
	        			       }
		                   }, 
	                       {
		            	       xtype: 'checkbox',
		            	       name: r.data.id,
		            	       id: r.data.id
		                   }, 
	                       { 
		            	       xtype: 'displayfield',
		                	       value: text,
		            	       autoHeight: true,
		            	       id: 'title_'+ r.data.id 
		                   }
		                ]
	
	            });
            }

            else 
            {
                new_column = {
		                xtype: 'fieldset',
		                layout: 'column',
		                id: 'column_'+r.data.id,
		                name: timeblock[1]+r.data.title,
		                items: []
                }
                new_column.items.push({
                    xtype: 'combo',
                    hiddenName: 'priority_' + r.data.id,
                    hiddenID: 'priority_' + r.data.id,
                    id: 'combo_' + r.data.id,
                    name: 'combo_' + r.data.id,
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
                    id: 'title_'+ r.data.id 
	            });
	            this.add(new_column)
            }
        }
    },

    checkPriorities: function () {
        var priorities = new Array(this.priorityLimit + 1);
        for(i=0; i <= this.priorityLimit; ++i) {
            priorities[i] = 0;
        }

        var ids = checkbox_ids_by_timeblock[this.id()].split('_');
        for(i=0; i < ids.length - 1; ++i) 
        {
            //if (++priorities[parseInt(tab.items[i].items[0].getValue())] > 1) {
            if (parseInt(Ext.getCmp("combo_"+ids[i]).getValue()) && ++priorities[Ext.getCmp("combo_"+ids[i]).getValue()] > 1) 
            {
                alert("You assigned multiple classes to have the same priority. Please fix this.");
                this.show();
                return false;
            }
        }
        return true;
    }
});

Ext.reg('timeslotpanel', TimeslotPanel)
