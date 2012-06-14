Ext.define('LU.view.class.Card', {

    extend: 'Ext.NavigationView',
    xtype: 'classContainer',

    config: {

        title: 'Browse',
        iconCls: 'search',

        autoDestroy: false,

        items: [
            {
                xtype: 'classList'
            }
        ]
    }
});

