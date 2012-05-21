ClassCheckboxes = Ext.extend(Ext.form.FieldSet, { 

    ESPClassInfo: {},
    timeblockId: "",
    sectionId: 0,
    alreadyChecked: false,
    alreadyFlagged: false,
    isWalkin: false,

    initComponent: function ()
    {
        Ext.QuickTips.init();
        //comes up with label for checkboxes
        classText = this.getClassFullTitle();
        var config = 
        {
            layout: 'table',
	    layoutConfig: {columns: 4},
            border: false,
            id: this.timeblockId + this.ESPClassInfo.id,
            items: 
            [
                {
                    id: 'column1',
                    border: false,
		    xtype: 'button',
		    text: "Catalog info",
		    padding: 2,
		    onClick: this.showCatalogInfo
                },
	        {
		    xtype: 'radio',
		    id: 'flag_'+ this.sectionId,
		    hidden: this.isWalkin,
		    name: 'flag_'+this.timeblockId,
		    inputValue: this.sectionId,
		    checked: this.alreadyFlagged,
		    listeners: { } //listener changes the flagged classes box at the top when the flagged class changes
		},
         	{
		    xtype: 'checkbox',
		    hidden: this.isWalkin,
		    name: this.sectionId,
		    checked: this.alreadyChecked,
		    id: this.sectionId
		},
                { 
                    id: 'column3',
                    columnWidth: 0.9,
                    border: false,
		    xtype: 'displayfield',
		    value: classText,
		    id: 'title_'+ this.sectionId
		}
            ]
        };

        Ext.apply(this, Ext.apply(this.initialConfig, config));
        ClassCheckboxes.superclass.initComponent.apply(this, arguments); 
    },

    showCatalogInfo: function () 
    {
        Ext.Msg.alert(this.ownerCt.getClassFullTitle(), this.ownerCt.catalogText());
    },

    catalogText: function ()
    {
        //console.log(this.ESPClassInfo);
        var text = "";
        var tabText = "&nbsp;&nbsp;&nbsp;&nbsp;";

        text = text + "<b>Description:</b><br> " + tabText +this.ESPClassInfo.data.class_info + "<br>";
        text = text + "<b>Teachers:</b><br> ";
        var i;
        for(i = 0; i < this.ESPClassInfo.data.teachers.length; i ++)
        {
            var teacher = this.ESPClassInfo.data.teachers[i];         
            text = text + tabText + teacher.first_name + " " + teacher.last_name + "<br>";
        }
        
        if(!this.isWalkin){
            text = text + "<b>Size limit:</b> " + this.ESPClassInfo.data.class_size_max + "<br>";
        }

        text = text + "<b>Sections:</b><br>";
        var section;
        for(i = 0; i < this.ESPClassInfo.data.get_sections.length; i++)
        {
            section = this.ESPClassInfo.data.get_sections[i];
            var sectionText = tabText;
	    if (!section.get_meeting_times[0])
	    {
		console.log("Warning, no meeting times for section " + section.id);
	    }
	    else
	    {
		sectionText = sectionText + this.getDayOfWeekFromFullDate(section.get_meeting_times[0].start)
                sectionText = sectionText + this.getTimeOnlyFromFullDate(section.get_meeting_times[0].start);
                sectionText = sectionText + " - " + this.getTimeOnlyFromFullDate(section.get_meeting_times[section.get_meeting_times.length-1].end);
                text = text + sectionText + "<br>";
	    }
        }
        
        return text;
    },

    getTimeOnlyFromFullDate: function(full_date)
    {
        return full_date.substring(11, 16);
    },

    //number 19 hardcoded for Splash 2011.  Will someday dehackify this method
    getDayOfWeekFromFullDate: function(full_date) {
        if(full_date.substring(8, 10) == "19"){
            return "Sat ";
        }
        else{
            return "Sun ";
        }
    },

    getClassFullTitle: function ()
    {
        return this.ESPClassInfo.data.category.symbol + this.ESPClassInfo.data.id + ': ' + this.ESPClassInfo.data.title;
    },

    classNumber: function () 
    {
        return this.sectionId;
    },

    isChecked: function () 
    {
        return this.items.items[2].getValue();
    },

    isFlagged: function ()
    {
        return this.items.items[1].getValue();
    }
});

Ext.reg('class_checkboxes', ClassCheckboxes);
