Ext.define('LU.view.class.Prereq', {
    extend: 'Ext.List',
    xtype: 'prereqList',

    config: {
        disableSelection: true,
        store: 'Classes',
        itemTpl: Ext.create('Ext.XTemplate',
            '{[ values.prereqs.length > 0 ? values.prereqs : "None" ]}'
        )
    }
});
