/**
 * This custom panel adds in the CSRF token with every form submit.
 */
Ext.define('LU.view.base.Panel', {
    extend: 'Ext.form.Panel',

    submit: function(options) {
        function getCookie(name) {
           var cookieValue = null;
           if (document.cookie && document.cookie != '') {
               var cookies = document.cookie.split(';');
               for (var i = 0; i < cookies.length; i++) {
                   var cookie = Ext.String.trim(cookies[i]);
                   // Does this cookie string begin with the name we want?
                   if (cookie.substring(0, name.length + 1) == (name + '=')) {
                       cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                       break;
                   }
               }
           }
           return cookieValue;
        }

        function sameOrigin(url) {
           // url could be relative or scheme relative or absolute
           var host = document.location.host; // host + port
           var protocol = document.location.protocol;
           var sr_origin = '//' + host;
           var origin = protocol + sr_origin;
           // Allow absolute or scheme relative URLs to same origin
           return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
               (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
               // or any other URL that isn't scheme relative or absolute i.e relative.
               !(/^(\/\/|http:|https:).*/.test(url));
        }

        function safeMethod(method) {
           return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
        }

        var token = '';
        if (!safeMethod(options.method) && sameOrigin(options.url)) {
            token = getCookie('csrftoken');
        }

        options = Ext.apply({
            headers: Ext.apply(
                {'X-CSRFToken':  token},
                options.headers || {}
            )
        }, options || {});
        return this.superclass.superclass.submit.call(this, options);
    }
});

