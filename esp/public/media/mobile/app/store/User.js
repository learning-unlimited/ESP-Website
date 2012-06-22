Ext.define('LU.store.User', {
    extend: 'Ext.data.Store',

    requires: [ 'Ext.data.proxy.LocalStorage' ],

    config: {
        model: 'LU.model.User',

        proxy: {
            type: 'localstorage',
            id: 'ludev-user'
        }
    }
});
