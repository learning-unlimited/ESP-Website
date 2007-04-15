<Location "/code/esp-project">
    AuthBasicAuthoritative Off

    DAV svn
    SVNPath /esp/svn/esp
    SVNAutoVersioning On
    AuthType Basic
    AuthName "MIT ESP Subversion Respository"

    SetEnv DJANGO_SETTINGS_MODULE esp.settings
    PythonOption DJANGO_SETTINGS_MODULE esp.settings
    PythonAuthenHandler esp.users.apache_auth
    PythonOption ESPPermissionName V/Administer/Edit
    PythonOption DjangoRequireSuperuserStatus on
    <LimitExcept GET PROPFIND OPTIONS REPORT>
        Require valid-user
    </LimitExcept>
</Location>
<Location "/code/svn">
    AuthBasicAuthoritative Off

    DAV svn
    SVNPath /esp/svn/esp
    SVNAutoVersioning On
    AuthType Basic
    AuthName "MIT ESP Subversion Respository"

    SetEnv DJANGO_SETTINGS_MODULE esp.settings
    PythonOption DJANGO_SETTINGS_MODULE esp.settings
    PythonAuthenHandler esp.users.apache_auth
    PythonOption ESPPermissionName V/Administer/Edit
    PythonOption DjangoRequireSuperuserStatus on
    <LimitExcept GET PROPFIND OPTIONS REPORT>
        Require valid-user
    </LimitExcept>
</Location>
