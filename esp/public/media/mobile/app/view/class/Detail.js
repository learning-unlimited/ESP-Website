Ext.define('LU.view.class.Detail', {
    extend: 'Ext.Container',
    xtype: 'classDetail',

    config: {
        layout: 'vbox',
        scrollable: 'vertical',
        items: [
            {
                xtype: 'classInfo'
            },
            {
                xtype: 'classPrereqList'
            },
            {
                xtype: 'timingList'
            }
        ]
    }
});
