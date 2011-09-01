TimeslotPanel = Ext.extend(Ext.FormPanel, {

    ESPclasses: [],
    timeblock: [],
    oldPreferences: {},

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
            section_id = this.getSectionId(r);
            status = this.enrollmentStatus(section_id);
            console.log("status = " + status);

            if (priority_limit == 1) {
		        this.add({
                    xtype: 'class_checkboxes',
                    ESPClassInfo: r,
                    timeblockId: this.timeblock[0],
                    sectionId: section_id,
                    initialStatus: status
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

    getSectionId: function (r)
    {
        var i;
        for(i = 0; i < r.data.get_sections.length; i ++)
        {
            section = r.data.get_sections[i];      
            if(section.get_meeting_times[0].id == this.timeblock[0])
            {
                return section.id;
            }
        }
        //there should be error handling here
        return 0;
    },

    enrollmentStatus: function (sectionId) 
    {
        preferenceIndex = this.oldPreferences.findExact("section_id", sectionId);
        if(preferenceIndex >= 0 )
        {
            preference = this.oldPreferences.getAt(preferenceIndex);
            return preference.data.type;
        }
    },

    flaggedClass: function () {
        for(j=1; j<this.items.items.length; j++) {
	         var checkbox = this.items.items[j];
	         if(checkbox.isFlagged()){
                return checkbox;
             }
	     }
    },

    checkedClasses: function () {
        var checked = [];
        for(j=1; j<this.items.items.length; j++) {
	         var checkbox = this.items.items[j];
	         if(checkbox.isChecked()){
                checked.push(checkbox);
             }
	     }
        return checked;
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

    getNewPreferences: function () {
        classPreferences = new Object();
        for(j=1; j<this.items.items.length; j++) {
	         var checkbox = this.items.items[j];
             classPreferences[checkbox.classNumber()] = checkbox.isChecked();
	         classPreferences["flag_" + checkbox.classNumber()] = checkbox.isFlagged();
	     }
        return classPreferences;
    },

    getSummary: function () {
        var summaryParts =  [];
        summaryParts.push("<font size=\"5\">" + this.timeblock[1] + "</font>");
        var flagged = this.flaggedClass();
        summaryParts.push("<b>Flagged Class: </b>");
        if (!flagged){
            summaryParts.push("<font color=\"red\">None</font>");
        }
        else{
            summaryParts.push(flagged.classFullTitle);
        }

        summaryParts.push("<b>Classes with interest: </b>");
        var checked = this.checkedClasses()
        if(checked.length == 0)
        {
            summaryParts.push("<font color=\"red\">None</font>");
        }        
        for(j = 0; j < checked.length; j++)
        {
            checkbox = checked[j];
            summaryParts.push("    " + checkbox.classFullTitle);
        }      

        var summary = "";
        for(j = 0; j < summaryParts.length; j++){
            part = summaryParts[j];
            summary = summary + part + "<br />";
        }
        return summary;
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
