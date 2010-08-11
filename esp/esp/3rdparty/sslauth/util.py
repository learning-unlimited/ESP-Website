from django.conf import settings


X509_KEYS = {
    'subject_c': 'SSL_CLIENT_S_DN_C',
    'subject_st': 'SSL_CLIENT_S_DN_ST',
    'subject_l': 'SSL_CLIENT_S_DN_L',
    'subject_o': 'SSL_CLIENT_S_DN_O',
    'subject_ou': 'SSL_CLIENT_S_DN_OU',
    'subject_cn': 'SSL_CLIENT_S_DN_CN',
    'subject_t': 'SSL_CLIENT_S_DN_T',
    'subject_i': 'SSL_CLIENT_S_DN_I',
    'subject_g': 'SSL_CLIENT_S_DN_G',
    'subject_s': 'SSL_CLIENT_S_DN_S',
    'subject_d': 'SSL_CLIENT_S_DN_D',
    'subject_uid': 'SSL_CLIENT_S_DN_UID',
    'subject_email': 'SSL_CLIENT_S_DN_Email',
    'issuer_c': 'SSL_CLIENT_I_DN_C',
    'issuer_st': 'SSL_CLIENT_I_DN_ST',
    'issuer_l': 'SSL_CLIENT_I_DN_L',
    'issuer_o': 'SSL_CLIENT_I_DN_O',
    'issuer_ou': 'SSL_CLIENT_I_DN_OU',
    'issuer_cn': 'SSL_CLIENT_I_DN_CN',
    'issuer_t': 'SSL_CLIENT_I_DN_T',
    'issuer_i': 'SSL_CLIENT_I_DN_I',
    'issuer_g': 'SSL_CLIENT_I_DN_G',
    'issuer_s': 'SSL_CLIENT_I_DN_S',
    'issuer_d': 'SSL_CLIENT_I_DN_D',
    'issuer_uid': 'SSL_CLIENT_I_DN_UID',
    'issuer_email': 'SSL_CLIENT_I_DN_Email',
    'serial': 'SSL_CLIENT_M_SERIAL', 
    'cert': 'SSL_CLIENT_CERT',
    'verify': 'SSL_CLIENT_VERIFY',
}


def settings_get(key):
    """
    helper function to ease access to settings module
    """
    if hasattr(settings, key):
        return settings.__getattr__(key)
    else:
        return None


class SSLInfo(object):
    """
    Encapsulates the SSL environment variables in a read-only object. It attempts to find
    the ssl vars based on the type of request passed to the constructor. Currently only
    WSGIRequest and ModPythonRequest are supported.
    """
    def __init__(self, request):
        name = request.__class__.__name__
        if settings_get('SSLAUTH_FORCE_ENV'):
            env = settings_get('SSLAUTH_FORCE_ENV')
        elif name == 'WSGIRequest':
            env = request.environ
        elif name == 'ModPythonRequest':
            env = request._req.subprocess_env
        else:
            raise EnvironmentError, 'SSLAuth currently only works with mod_python or wsgi requests'
        self.read_env(env);
        pass
    
    def read_env(self, env):
        for attr,key in X509_KEYS.iteritems():
            if env.has_key(key) and env[key]:
                self.__dict__[attr] = env[key]
            else:
                self.__dict__[attr] = None
                
        if self.__dict__['verify'] == 'SUCCESS':
            self.__dict__['verify'] = True
        else:
            self.__dict__['verify'] = False
    
    def get(self, attr):
        return self.__getattr__(attr)
    
    def get_dict(self, prefix):
        dict = {}
        for key in X509_KEYS.keys():
            if key.startswith(prefix):
                dict[key] = self.__dict__[key]
        return dict
    
    def get_subject(self):
        return self.get_dict('subject_')
    
    def get_issuer(self):
        return self.get_dict('issuer_')
    
    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            raise AttributeError, 'SSLInfo does not contain key %s' % attr
        
    def __setattr__(self, attr, value):
        raise AttributeError, 'SSL vars are read only!'
