Ext.define('LU.controller.Register', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            registerForm: 'registerForm'
        },

        control: {
            'registerForm field': {
                action: 'onSubmit'
            },
            'registerForm button': {
                tap: 'onSubmit'
            }
        }
    },

    onSubmit: function() {
        LU.Util.showLoadingMask();

        this.getRegisterForm().submit({
            url: LU.Util.getStudentRegistrationUrl(),
            success: function(form, result) {
                var registerForm = this.getRegisterForm(),
                    studentId = result.user_id;

                // refresh student store
                Ext.getStore('Students').load({
                    callback: function(records, operation, success) {
                        if (success) {
                            // clear values for form fields
                            var fields = registerForm.query('field'), i;
                            for (i = 0; i < fields.length; i++) {
                                fields[i].reset();
                            }

                            // get tabpanel and display Search tab
                            var tabPanel = registerForm.up('onsite');
                            tabPanel.setActiveItem(0);

                            // display student detail view
                            var index = this.find('id', studentId),
                                record = this.getAt(index),
                                studentList = tabPanel.down('studentList');
                            studentList.fireEvent('itemtap', studentList, index, null, record);

                            LU.Util.hideLoadingMask();
                        } else {
                            LU.Util.setLoadingMask('Failed to add user', 'error', false);
                            LU.Util.hideLoadingMask(3000);
                        }
                    }
                });
            },
            failure: function(form, result) {
                LU.Util.setLoadingMask('Failed to add user', 'error', false);
                LU.Util.hideLoadingMask(3000);
            },
            scope: this
        });
    }
});
