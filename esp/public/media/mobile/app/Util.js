Ext.define('LU.Util', {

    singleton: true,

    constructor: function(config) {
        this.initConfig(config);
        this.callParent([config]);
    },

    getCatalogUrl: function() {
        var user = Ext.getStore('User').first();
        var baseUrl = user.getProgram().get('baseUrl');
        return '/learn/' + baseUrl + '/catalog_json';
    }
});
