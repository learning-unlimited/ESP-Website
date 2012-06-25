Ext.define('LU.view.class.Info', {
    extend: 'Ext.Component',
    xtype: 'classInfo',

    config: {
        cls: 'classInfo',
        tpl: Ext.create('Ext.XTemplate',
            '<div class="title">{title} <div class="code">{code}</div></div>',
            '<div class="description">{class_info}</div>'
        )
   }
});
