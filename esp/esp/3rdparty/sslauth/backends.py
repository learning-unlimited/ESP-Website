from django.db.models import Q
from django.db import transaction
from django.contrib.auth.models import User, UserManager

from util import settings_get
from models import ClientCertificate, DistinguishedName

class AuthenticationError(Exception):
    pass

class SSLAuthBackend:
    """
    authenticates a client certificate against the records stored 
    in ClientCertificate model and looks up the corresponding django user

    In all methods, the ssl_info parameter is supposed to be an SSLInfo instance
    """

    # At the moment, we don't support any authz stuff, so the value shouldn't
    # matter
    # If we start supporting authz, it would be good to support these being
    # set to true --- I think we might be required to in a few versions?
    supports_anonymous_user = True
    supports_inactive_user = True
    supports_object_permissions = True
    
    def authenticate(self, ssl_info):
        cert = self.get_certificate(ssl_info)
        if cert is None:
            return None
        else:
            return cert.user


    def get_user(self, user_id):
        """
        simply return the user object. That way, we only need top look-up the 
        certificate once, when loggin in
        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


    def get_certificate(self, ssl_info):
        """
        returns a ClientCertificate object for the passed
        cert data or None if not found
        """
        
        if settings_get('SSLAUTH_STRICT_MATCH'):
            # compare complete certificate in strict match
            if not ssl_info.cert:
                raise EnvironmentError, 'SSLAuth: strict match required but PEM encoded certificate not found in environment. Check your server settings'
            query = Q(cert=ssl_info.cert)
        else:
            # compare according to SSLAUTH_SUBJECT_MATCH_KEYS
            if settings_get('SSLAUTH_SUBJECT_MATCH_KEYS'):
                match_keys = settings_get('SSLAUTH_SUBJECT_MATCH_KEYS')
            else:
                match_keys = ( 'subject_email', 'subject_cn', 'subject_o' )

            query_args = {}
            for key in match_keys:
                if not ssl_info.get(key):
                    return None
                    #raise AuthenticationError, 'key %s is missing from ssl_info' % key
                query_args[key.replace('_', '__')] = ssl_info.get(key)

            query = Q(**query_args)
        try:
            cert = ClientCertificate.objects.select_related().get(query)
            return cert
        except ClientCertificate.DoesNotExist:
            return None


    @transaction.commit_on_success
    def create_user(self, ssl_info):
        """
        This method creates a new django User and ClientCertificate record 
        for the passed certificate info. It does not create an issuer record,
        just a subject for the ClientCertificate.
        """
        # auto creation only created a DN for the subject, not the issuer
        subject = DistinguishedName()
        for attr,val in ssl_info.get_subject().iteritems():
            if not val: val = ''
            subject.__setattr__(attr.replace('subject_',''), val)
        subject.save()

        # get username and check if the user exists already
        if settings_get('SSLAUTH_CREATE_USERNAME_CALLBACK'):
            build_username = settings_get('SSLAUTH_CREATE_USERNAME_CALLBACK')
        else:
            build_username = self.build_username
            
        username = build_username(ssl_info)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            if settings_get('SSLAUTH_CREATE_USER_CALLBACK'):
                build_user = settings_get('SSLAUTH_CREATE_USER_CALLBACK')
            else:
                build_user = self.build_user
            user = build_user(username, ssl_info)
        
        # create the certificate record and save
        cert = ClientCertificate()
        cert.user = user
        cert.subject = subject
        if ssl_info.cert:
            cert.cert = ssl_info.cert
        if ssl_info.serial:
            cert.serial = ssl_info.serial
        cert.save()
            
        return user


    def build_username(self, ssl_info):
        """
        create a valid django username from the certificate info. this method
        can be "overwritten" by using the SSLAUTH_CREATE_USERNAME_CALLBACK setting
        """
        import re
        return re.sub(r'[^a-zA-Z0-9_-]', '_', ssl_info.subject_email)


    def build_user(self, username, ssl_info):
        """
        create a valid (and stored) django user to be associated with the newly 
        created certificate record. This method can be "overwritten" by using the 
        SSLAUTH_CREATE_USER_CALLBACK setting.
        """
        name_parts = ssl_info.subject_cn.split()
        user = User()
        user.username=username
        user.password=UserManager().make_random_password()
        user.first_name = " ".join(name_parts[:-1])
        user.last_name = name_parts[-1]
        user.email = ssl_info.subject_email
        user.is_active = True
        user.save()
        return user
