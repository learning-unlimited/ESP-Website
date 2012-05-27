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
                var main;
                if (result.isStudent === 'true') {
                    main = Ext.widget('mainStudent');
                } else if (result.isVolunteer == 'true') {
                    main = Ext.widget('mainVolunteer');
                } else {
                    // display error message for unknown role
                    console.log('unknown role');
                    return;
                }
                Ext.Viewport.setActiveItem(main);
            },
            failure: function(form, result) {
                console.log('failed :(');
            },
            params: {
                // tells the server that we are logging in using mobile site
                'isMobile': true
            }
        });
    }
});

