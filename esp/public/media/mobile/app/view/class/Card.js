Ext.define('LU.view.class.Card', {

    extend: 'Ext.NavigationView',
    xtype: 'classContainer',

    config: {

        title: 'Classes',
        iconCls: 'time',

        autoDestroy: false,

        items: [
            {
                xtype: 'classList'
            }
        ]
    }
});

