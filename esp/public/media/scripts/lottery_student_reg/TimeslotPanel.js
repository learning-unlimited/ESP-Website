TimeslotPanel = Ext.extend(Ext.FormPanel, { 
    initComponent: function() {
        TimeslotPanel.superclass.initComponent.apply(this, arguments); 
    }
});

Ext.reg('timeslotpanel', TimeslotPanel)
