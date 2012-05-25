Ext.define('LU.controller.Login', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            loggedOut: 'loggedOut'
        },
        control: {
            '#password': {
                action: 'onLogin'
            }
        }
    },

    onLogin: function(textfield) {
        this.getLoggedOut().submit({
            url: '/myesp/ajax_login/',
            method: 'POST',
            success: function(form, result) {
                console.log('login successful!');
            },
            failure: function(form, result) {
                console.log(result);
                console.log('failed :(');
            }
        });
    }
});

