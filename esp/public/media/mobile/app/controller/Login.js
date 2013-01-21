Ext.define('LU.controller.Login', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            loginForm: 'loginForm',
            usernameField: 'loginForm textfield',
            passwordField: 'loginForm passwordfield',
            main: 'main'
        },
        control: {
            passwordField: {
                action: 'onLogin'
            }
        }
    },

    onLogin: function(textfield) {
        if (this.getUsernameField().getValue() != '' && this.getPasswordField().getValue() != '') {
            this.getLoginForm().submit({
                url: '/myesp/ajax_login/',
                method: 'POST',
                params: {
                    // tells the server that we are logging in using mobile site
                    'isMobile': true
                },

                success: function(form, result) {
                    var program = Ext.widget('programList');
                    var role = '';

                    if (result.isAdmin == 'true') {
                        role = 'admin';
                    } else if (result.isOnsite === 'true') {
                        role = 'onsite';
                    } else if (result.isStudent == 'true') {
                        role = 'student';
                    } else {
                        // display error message for unknown role
                        Ext.Msg.alert('Unauthorized Role', 'You have to be an administrator, student, or onsite user to access the app.');
                        return;
                    }

                    // stores the user's role in localstorage
                    // (we need this to determine which interface to show later)
                    var user = Ext.getStore('User');
                    user.removeAll();
                    user.add({role: role});
                    user.sync();

                    Ext.Viewport.getActiveItem().destroy();
                    Ext.Viewport.setActiveItem(program);
                },

                failure: function(form, result) {
                    console.log(result);
                    if (result.message) {
                        Ext.Msg.alert('Login Error', result.message);
                    } else if (result.statusText) {
                        Ext.Msg.alert('Login Error', 'An error has occurred. (' + result.statusText + ')')
                    } else {
                        Ext.Msg.alert('Login Error', 'An unknown error has occurred. You may wish to try logging again later.');
                    }
                }
            });
        } else {
            var field_string = '';
            if (this.getUsernameField().getValue() === '') field_string = 'username';
            if (this.getPasswordField().getValue() === '') field_string += (field_string === '') ? 'password' : ' and password';
            Ext.Msg.alert('Invalid Form', 'You did not provide your ' + field_string + '.');
        }
    }
});

