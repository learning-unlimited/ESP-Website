/**
 * This custom panel adds in the CSRF token with every form submit.
 */
Ext.define('LU.view.base.Panel', {
    extend: 'Ext.form.Panel',

    submit: function(options) {
        options = Ext.apply({
            headers: Ext.apply(
                {'X-CSRFToken':  LU.Util.getCsrfToken(options)},
                options.headers || {}
            )
        }, options || {});
        return this.superclass.superclass.submit.call(this, options);
    }
});

