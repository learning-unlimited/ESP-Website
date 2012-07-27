Ext.define('LU.controller.Main', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            onsiteContainer: 'onsite',
        },

        control: {
            onsiteContainer: {
                activeitemchange: 'onOnsiteTabChange'
            },
        }
    },

    onOnsiteTabChange: function(container, value, oldValue, opts) {
        if (value.config.xtype === 'classContainer') {
            var classStore = Ext.getStore('Classes');
            if (!LU.Util.getIsClassStoreLoaded()) {
                LU.Util.showLoadingMask();
                // value.down('button[text="Logout"]').hide();
                value.getNavigationBar().hide();

                LU.Util.getCatalog(function() {
                    LU.Util.hideLoadingMask();
                });
            }
        }
    },
});
