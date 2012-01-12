from .models import DistinguishedName, ClientCertificate
from esp.admin import admin_site

admin_site.register(DistinguishedName)
admin_site.register(ClientCertificate)
