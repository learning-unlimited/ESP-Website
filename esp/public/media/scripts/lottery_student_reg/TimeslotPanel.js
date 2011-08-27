TimeslotPanel = Ext.extend(Ext.FormPanel, {

    ESPclasses: [],
    timeblock: [],

    initComponent: function() {
        var config =
        {
            items:
            [
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
                }
            ],
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
            var checkbox_id = r.data.id;

		    //comes up with label for checkboxes
		    text = '';
		    text = text + r.data.category.symbol + r.data.id + ': ' + r.data.title + ', ';
		    //end_timeblock = r.data.get_sections[j].get_meeting_times[r.data.get_sections[j].get_meeting_times.length-1];
		    //text = text + timeblock.start.substring(11,16) //+ ' - ' + end_timeblock.end.substring(11,16);
        
            if (priority_limit == 1) {
		        this.add({
                    xtype: 'class_checkboxes',
                    ESPClassInfo: r,
                    timeblockId: this.timeblock[1],
                    id: this.timeblock[1] + r.id,
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

    flaggedClass: function () {
        return ;
    },

    //return true if a class is flagged.
    timeslotCompleted: function () {
        for(i = 1; i < this.items.items.length; i ++)
        {
            var classFieldSet = this.items.items[i];
            if(classFieldSet.items.items[0].getValue() == true)
            {
                return true;
            }
        }
        return false;
    },

    getPreferences: function () {
        classPreferences = new Object();
        noPreferenceRadio = this.items.items[0].items.items[0];
        classPreferences[noPreferenceRadio.id] = noPreferenceRadio.getValue();
        for(j=1; j<this.items.items.length; j++) {
	         var checkbox = this.items.items[j];
             console.log(checkbox);
             console.log(checkbox.id);
             classPreferences[checkbox.id] = checkbox.items.items[1].getValue();
	         classPreferences["flag_" + checkbox.id] = checkbox.items.items[0].getValue();
	     }
        return classPreferences;
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
